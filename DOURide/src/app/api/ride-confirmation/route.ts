/**
 * API Route: Student Ride Confirmation
 * POST /api/ride-confirmation
 * GET  /api/ride-confirmation?date=YYYY-MM-DD
 * 
 * Handles student confirmation/cancellation for next-day rides.
 * Requires JWT authentication — userId is extracted from the token.
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { getSupabaseAdmin } from "@/lib/supabase-admin";

/**
 * Verify JWT from Authorization header and return the authenticated user's ID.
 */
async function getAuthenticatedUserId(request: NextRequest): Promise<string | null> {
    const authHeader = request.headers.get("authorization");
    if (!authHeader?.startsWith("Bearer ")) {
        return null;
    }
    const token = authHeader.split(" ")[1];

    const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
        return null;
    }
    return user.id;
}

export async function POST(request: NextRequest) {
    // Authenticate
    const authenticatedUserId = await getAuthenticatedUserId(request);
    if (!authenticatedUserId) {
        return NextResponse.json(
            { error: "Unauthorized: Giriş yapmanız gerekiyor." },
            { status: 401 }
        );
    }

    try {
        const body = await request.json();
        const { action, rideDate, pickupTime, dropoffTime, notes } = body;

        // userId comes from the token, not from the body
        const userId = authenticatedUserId;

        if (!action || !rideDate) {
            return NextResponse.json(
                { error: "action and rideDate are required" },
                { status: 400 }
            );
        }

        if (!["confirm", "cancel", "change"].includes(action)) {
            return NextResponse.json(
                { error: "Invalid action. Must be 'confirm', 'cancel', or 'change'" },
                { status: 400 }
            );
        }

        const adminClient = getSupabaseAdmin();

        // Check deadline (22:00 previous day)
        const now = new Date();
        const rideDateObj = new Date(rideDate);
        const deadline = new Date(rideDateObj);
        deadline.setDate(deadline.getDate() - 1);
        deadline.setHours(22, 0, 0, 0);

        const isPastDeadline = now > deadline;

        // Determine status based on action and deadline
        let status: string;
        if (action === "confirm") {
            status = isPastDeadline ? "pending_admin_approval" : "confirmed";
        } else if (action === "cancel") {
            status = "cancelled_by_student";
        } else {
            status = "pending_admin_approval";
        }

        // Check if a ride request already exists for this date
        const { data: existingRide, error: findError } = await adminClient
            .from("ride_requests")
            .select("*")
            .eq("user_id", userId)
            .gte("requested_pickup_time", `${rideDate}T00:00:00`)
            .lt("requested_pickup_time", `${rideDate}T23:59:59`)
            .single();

        if (findError && findError.code !== "PGRST116") {
            throw findError;
        }

        let result;
        if (existingRide) {
            // Update existing ride
            const { data, error } = await (adminClient as any)
                .from("ride_requests")
                .update({
                    status,
                    notes: notes || (existingRide as any).notes,
                    updated_at: new Date().toISOString(),
                })
                .eq("id", (existingRide as any).id)
                .select()
                .single();

            if (error) throw error;
            result = data;
        } else if (action === "confirm") {
            // Create new ride request
            const { data: user, error: userError } = await adminClient
                .from("users")
                .select("home_address, home_coordinates")
                .eq("id", userId)
                .single();

            if (userError) throw userError;

            const { data, error } = await (adminClient as any)
                .from("ride_requests")
                .insert({
                    user_id: userId,
                    type: "scheduled",
                    status,
                    requested_pickup_time: `${rideDate}T${pickupTime || "08:00"}:00`,
                    requested_dropoff_time: `${rideDate}T${dropoffTime || "17:00"}:00`,
                    pickup_location: {
                        address: (user as any)?.home_address || "Ev Adresi",
                        coordinates: (user as any)?.home_coordinates,
                    },
                    dropoff_location: {
                        address: "Yıldız Teknik Üniversitesi Davutpaşa Kampüsü",
                        coordinates: { lat: 41.0254, lng: 28.8895 },
                    },
                    notes,
                })
                .select()
                .single();

            if (error) throw error;
            result = data;
        } else {
            return NextResponse.json(
                { error: "No existing ride to cancel or change" },
                { status: 404 }
            );
        }

        return NextResponse.json({
            success: true,
            action,
            status,
            isPastDeadline,
            message: getActionMessage(action, status, isPastDeadline),
            ride: result,
        });
    } catch (error: any) {
        console.error("Ride confirmation error:", error);
        return NextResponse.json(
            { error: error.message || "Confirmation failed" },
            { status: 500 }
        );
    }
}

function getActionMessage(action: string, status: string, isPastDeadline: boolean): string {
    if (action === "confirm") {
        if (isPastDeadline) {
            return "Onay süresi geçtiği için talebiniz yönetici onayına gönderildi.";
        }
        return "Servisiniz başarıyla onaylandı.";
    }
    if (action === "cancel") {
        return "Servisiniz iptal edildi.";
    }
    return "Değişiklik talebiniz yönetici onayına gönderildi.";
}

// GET: Check ride status for a specific date
export async function GET(request: NextRequest) {
    // Authenticate
    const authenticatedUserId = await getAuthenticatedUserId(request);
    if (!authenticatedUserId) {
        return NextResponse.json(
            { error: "Unauthorized: Giriş yapmanız gerekiyor." },
            { status: 401 }
        );
    }

    try {
        const { searchParams } = new URL(request.url);
        const date = searchParams.get("date");

        if (!date) {
            return NextResponse.json(
                { error: "date query parameter is required" },
                { status: 400 }
            );
        }

        // userId comes from the token
        const userId = authenticatedUserId;

        const adminClient = getSupabaseAdmin();
        const { data, error } = await adminClient
            .from("ride_requests")
            .select("*")
            .eq("user_id", userId)
            .gte("requested_pickup_time", `${date}T00:00:00`)
            .lt("requested_pickup_time", `${date}T23:59:59`)
            .single();

        if (error && error.code !== "PGRST116") {
            throw error;
        }

        // Check deadline
        const now = new Date();
        const rideDate = new Date(date);
        const deadline = new Date(rideDate);
        deadline.setDate(deadline.getDate() - 1);
        deadline.setHours(22, 0, 0, 0);

        return NextResponse.json({
            hasExistingRide: !!data,
            ride: data || null,
            isPastDeadline: now > deadline,
            deadline: deadline.toISOString(),
        });
    } catch (error: any) {
        console.error("Get ride status error:", error);
        return NextResponse.json(
            { error: error.message },
            { status: 500 }
        );
    }
}
