/**
 * API Route: Student Ride Confirmation
 * POST /api/ride-confirmation
 * 
 * Handles student confirmation/cancellation for next-day rides
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { userId, action, rideDate, pickupTime, dropoffTime, notes } = body;

        if (!userId || !action || !rideDate) {
            return NextResponse.json(
                { error: "userId, action, and rideDate are required" },
                { status: 400 }
            );
        }

        if (!["confirm", "cancel", "change"].includes(action)) {
            return NextResponse.json(
                { error: "Invalid action. Must be 'confirm', 'cancel', or 'change'" },
                { status: 400 }
            );
        }

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
        const { data: existingRide, error: findError } = await supabase
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
            const { data, error } = await supabase
                .from("ride_requests")
                .update({
                    status,
                    notes: notes || existingRide.notes,
                    updated_at: new Date().toISOString(),
                })
                .eq("id", existingRide.id)
                .select()
                .single();

            if (error) throw error;
            result = data;
        } else if (action === "confirm") {
            // Create new ride request
            const { data: user, error: userError } = await supabase
                .from("users")
                .select("home_address, home_coordinates")
                .eq("id", userId)
                .single();

            if (userError) throw userError;

            const { data, error } = await supabase
                .from("ride_requests")
                .insert({
                    user_id: userId,
                    type: "scheduled",
                    status,
                    requested_pickup_time: `${rideDate}T${pickupTime || "08:00"}:00`,
                    requested_dropoff_time: `${rideDate}T${dropoffTime || "17:00"}:00`,
                    pickup_location: {
                        address: user?.home_address || "Ev Adresi",
                        coordinates: user?.home_coordinates,
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
    try {
        const { searchParams } = new URL(request.url);
        const userId = searchParams.get("userId");
        const date = searchParams.get("date");

        if (!userId || !date) {
            return NextResponse.json(
                { error: "userId and date are required" },
                { status: 400 }
            );
        }

        const { data, error } = await supabase
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
