/**
 * Route Optimization API
 * Endpoint for optimizing routes using various strategies
 */

import { NextResponse } from "next/server";
import { headers } from "next/headers";
import { createClient } from "@supabase/supabase-js";
import { getStrategy, getAvailableStrategies, getDefaultStrategy } from "@/services/doubus/route-strategies";
import { calculateDistance } from "@/services/doubus/route";

// Create Supabase client with service role for admin operations
const supabaseAdmin = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Verify JWT and get user
async function verifyAuth(authHeader: string | null) {
    if (!authHeader?.startsWith("Bearer ")) {
        return null;
    }

    const token = authHeader.split(" ")[1];

    const { data: { user }, error } = await supabaseAdmin.auth.getUser(token);

    if (error || !user) {
        return null;
    }

    // Get user profile to check role
    const { data: profile } = await supabaseAdmin
        .from("users")
        .select("*")
        .eq("id", user.id)
        .single();

    return profile;
}

/**
 * GET /api/optimize-route
 * Returns available strategies
 */
export async function GET() {
    return NextResponse.json({
        strategies: getAvailableStrategies(),
        defaultStrategy: getDefaultStrategy().name,
    });
}

/**
 * POST /api/optimize-route
 * Optimizes a route using the specified strategy
 * 
 * Body:
 * {
 *   start: string,      // Starting location code
 *   end: string,        // Ending location code
 *   waypoints: string[], // Intermediate locations
 *   strategy?: string   // Optional: "permutation", "nearest-neighbor", "two-opt"
 * }
 */
export async function POST(request: Request) {
    try {
        const headersList = await headers();
        const authHeader = headersList.get("authorization");

        const user = await verifyAuth(authHeader);

        if (!user) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }

        // Only admins can optimize routes
        if (user.role !== "admin") {
            return NextResponse.json({ error: "Forbidden - Admin only" }, { status: 403 });
        }

        const body = await request.json();
        const { start, end, waypoints, strategy: strategyName } = body;

        // Validate input
        if (!start || !end) {
            return NextResponse.json(
                { error: "Missing required fields: start, end" },
                { status: 400 }
            );
        }

        if (!Array.isArray(waypoints)) {
            return NextResponse.json(
                { error: "waypoints must be an array" },
                { status: 400 }
            );
        }

        // Get the strategy
        const strategy = getStrategy(strategyName);

        if (!strategy) {
            return NextResponse.json(
                {
                    error: `Unknown strategy: ${strategyName}`,
                    availableStrategies: getAvailableStrategies()
                },
                { status: 400 }
            );
        }

        // Measure optimization time
        const startTime = performance.now();

        // Calculate optimal route
        const result = await strategy.calculateOptimalRoute(
            start,
            end,
            waypoints,
            calculateDistance
        );

        const endTime = performance.now();
        const optimizationTimeMs = Math.round(endTime - startTime);

        // Calculate total distance (approximation based on duration)
        // Assuming average speed of 40 km/h
        const totalDistanceKm = (result.totalDuration / 60) * 40;

        return NextResponse.json({
            success: true,
            strategy: strategy.name,
            route: {
                start,
                end,
                waypoints: result.routeDetails.map(d => d.location2).slice(0, -1),
                routeDetails: result.routeDetails,
                totalDurationMinutes: result.totalDuration,
                totalDistanceKm: Math.round(totalDistanceKm * 10) / 10,
            },
            meta: {
                waypointCount: waypoints.length,
                optimizationTimeMs,
            },
        });
    } catch (error: any) {
        console.error("Route optimization error:", error);
        return NextResponse.json(
            { error: error.message || "Internal server error" },
            { status: 500 }
        );
    }
}
