/**
 * API Route: Student Ride Confirmation
 * POST /api/ride-confirmation
 * GET  /api/ride-confirmation?date=YYYY-MM-DD
 * 
 * Handles student confirmation/cancellation for next-day rides.
 * Requires JWT authentication — userId is extracted from the token.
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { AppError, getCurrentUserFromRequest } from "@/lib/admin-auth";
import type { Database } from "@/lib/supabase";

const rideConfirmationSchema = z.object({
    action: z.enum(["confirm", "cancel", "change"], {
        errorMap: () => ({ message: "Invalid action. Must be 'confirm', 'cancel', or 'change'" }),
    }),
    rideDate: z.string().min(1, "rideDate is required"),
    pickupTime: z.string().optional(),
    dropoffTime: z.string().optional(),
    notes: z.string().optional(),
});

export async function POST(request: NextRequest) {
    try {
        const authUser = await getCurrentUserFromRequest(request);
        if (!authUser) {
            throw AppError.unauthorized("Unauthorized: Giriş yapmanız gerekiyor.");
        }

        const rawBody = await request.json();
        const parseResult = rideConfirmationSchema.safeParse(rawBody);
        if (!parseResult.success) {
            return NextResponse.json(
                { error: parseResult.error.errors[0].message },
                { status: 400 }
            );
        }

        const { action, rideDate, pickupTime, dropoffTime, notes } = parseResult.data;

        // userId comes from the token, not from the body
        const userId = authUser.id;

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
        const { data: existingRideRaw, error: findError } = await adminClient
            .from("ride_requests")
            .select("*")
            .eq("user_id", userId)
            .gte("requested_pickup_time", `${rideDate}T00:00:00`)
            .lt("requested_pickup_time", `${rideDate}T23:59:59`)
            .single();

        if (findError && findError.code !== "PGRST116") {
            throw findError;
        }

        const existingRide = existingRideRaw as Database["public"]["Tables"]["ride_requests"]["Row"] | null;
        let result;
        if (existingRide) {
            // Update existing ride
            const { data, error } = await adminClient
                .from("ride_requests")
                .update({
                    status,
                    notes: notes ?? existingRide.notes,
                    updated_at: new Date().toISOString(),
                } as never)
                .eq("id", existingRide.id)
                .select()
                .single();

            if (error) throw error;
            result = data;
        } else if (action === "confirm") {
            // Create new ride request
            const { data: userDataRaw, error: userError } = await adminClient
                .from("users")
                .select("home_address, home_coordinates")
                .eq("id", userId)
                .single();

            if (userError) throw userError;
            const userData = userDataRaw as Pick<Database["public"]["Tables"]["users"]["Row"], "homeAddress" | "homeCoordinates"> | null;

            const { data, error } = await adminClient
                .from("ride_requests")
                .insert({
                    user_id: userId,
                    type: "scheduled",
                    status,
                    requested_pickup_time: `${rideDate}T${pickupTime ?? "08:00"}:00`,
                    requested_dropoff_time: `${rideDate}T${dropoffTime ?? "17:00"}:00`,
                    pickup_location: {
                        address: userData?.homeAddress ?? "Ev Adresi",
                        coordinates: userData?.homeCoordinates,
                    },
                    dropoff_location: {
                        address: "Yıldız Teknik Üniversitesi Davutpaşa Kampüsü",
                        coordinates: { lat: 41.0254, lng: 28.8895 },
                    },
                    notes,
                } as never)
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
    } catch (error: unknown) {
        if (error instanceof AppError) {
            return NextResponse.json({ error: error.message }, { status: error.statusCode });
        }
        console.error("Ride confirmation error:", error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Confirmation failed" },
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
        const authUser = await getCurrentUserFromRequest(request);
        if (!authUser) {
            throw AppError.unauthorized("Unauthorized: Giriş yapmanız gerekiyor.");
        }

        const { searchParams } = new URL(request.url);
        const date = searchParams.get("date");

        if (!date) {
            return NextResponse.json(
                { error: "date query parameter is required" },
                { status: 400 }
            );
        }

        // userId comes from the token
        const userId = authUser.id;

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
    } catch (error: unknown) {
        if (error instanceof AppError) {
            return NextResponse.json({ error: error.message }, { status: error.statusCode });
        }
        console.error("Get ride status error:", error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : "Internal server error" },
            { status: 500 }
        );
    }
}
