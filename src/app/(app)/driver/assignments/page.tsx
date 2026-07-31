"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { format, parseISO, isToday, isTomorrow } from "date-fns";
import { tr } from "date-fns/locale";
import {
    Route,
    Clock,
    Users,
    MapPin,
    ChevronRight,
    Calendar,
    CheckCircle2,
    AlertCircle
} from "lucide-react";
import Link from "next/link";
import { adminApi } from "@/lib/admin-api";
import { getSupabaseClient } from "@/lib/supabase";
import type { RouteAssignment } from "@/types/db";
import type { Vehicle } from "@/types";

interface AssignmentWithDetails extends RouteAssignment {
    vehicle?: Vehicle;
    studentCount: number;
}

export default function DriverAssignmentsPage() {
    const { user } = useAuth();
    const { toast } = useToast();
    const [assignments, setAssignments] = useState<AssignmentWithDetails[]>([]);
    const [loading, setLoading] = useState(true);

    const loadAssignments = async () => {
        try {
            setLoading(true);
            const { data: { session } } = await getSupabaseClient().auth.getSession();
            if (!session?.access_token) {
                throw new Error("Unauthorized");
            }

            // Get all route assignments and filter by driver
            const [assignmentsData, vehiclesData] = await Promise.all([
                // Using admin API to get assignments - in production, create a driver-specific endpoint
                fetch("/api/driver/assignments", {
                    headers: {
                        "Authorization": `Bearer ${session.access_token}`,
                    },
                }).then(res => res.json()).catch(() => []),
                adminApi.vehicles.getAll().catch(() => [])
            ]);

            // Map assignments with vehicle details
            const enrichedAssignments: AssignmentWithDetails[] = (assignmentsData || [])
                .filter((a: RouteAssignment) => a.driverId === user?.id)
                .map((assignment: RouteAssignment) => ({
                    ...assignment,
                    vehicle: vehiclesData.find((v: Vehicle) => v.id === assignment.vehicleId),
                    studentCount: assignment.studentIds?.length || 0
                }))
                .sort((a: AssignmentWithDetails, b: AssignmentWithDetails) =>
                    new Date(a.pickupTime).getTime() - new Date(b.pickupTime).getTime()
                );

            setAssignments(enrichedAssignments);
        } catch (error: any) {
            console.error("Error loading assignments:", error);
            toast({
                title: "Yükleme Hatası",
                description: "Görevler yüklenirken bir hata oluştu.",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (user?.id) {
            // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount initial data load; loading flag flips synchronously. Upstream fix: data-fetching framework.
            loadAssignments();
        }
    }, [user?.id]);

    const getStatusBadge = (status: RouteAssignment["status"]) => {
        const config = {
            scheduled: { label: "Planlandı", variant: "default" as const, icon: Clock },
            in_progress: { label: "Devam Ediyor", variant: "secondary" as const, icon: Route },
            completed: { label: "Tamamlandı", variant: "outline" as const, icon: CheckCircle2 },
            cancelled: { label: "İptal", variant: "destructive" as const, icon: AlertCircle },
        };
        const { label, variant, icon: Icon } = config[status];
        return (
            <Badge variant={variant} className="flex items-center gap-1">
                <Icon className="h-3 w-3" />
                {label}
            </Badge>
        );
    };

    const getDateLabel = (dateStr: string) => {
        const date = parseISO(dateStr);
        if (isToday(date)) return "Bugün";
        if (isTomorrow(date)) return "Yarın";
        return format(date, "dd MMMM", { locale: tr });
    };

    const todayAssignments = assignments.filter(a =>
        isToday(parseISO(a.date)) && a.status !== "completed" && a.status !== "cancelled"
    );

    const upcomingAssignments = assignments.filter(a =>
        !isToday(parseISO(a.date)) && a.status === "scheduled"
    );

    const completedToday = assignments.filter(a =>
        isToday(parseISO(a.date)) && a.status === "completed"
    );

    if (!user || user.role !== "driver") {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Erişim Reddedildi</CardTitle>
                </CardHeader>
                <CardContent>
                    <p>Bu sayfayı görüntüleme yetkiniz yok.</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Route className="text-primary" />
                        Görevlerim
                    </h1>
                    <p className="text-muted-foreground">
                        Atanmış servis görevlerinizi görüntüleyin
                    </p>
                </div>
                <Button onClick={loadAssignments} variant="outline" disabled={loading}>
                    Yenile
                </Button>
            </div>

            {loading ? (
                <Card>
                    <CardContent className="py-8 text-center">
                        <p className="text-muted-foreground">Görevler yükleniyor...</p>
                    </CardContent>
                </Card>
            ) : (
                <>
                    {/* Today's Active Assignments */}
                    <Card className="border-l-4 border-l-primary">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Calendar className="h-5 w-5" />
                                Bugünkü Görevler
                            </CardTitle>
                            <CardDescription>
                                {todayAssignments.length > 0
                                    ? `${todayAssignments.length} aktif görev`
                                    : "Bugün için aktif görev yok"}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {todayAssignments.length === 0 ? (
                                <p className="text-center text-muted-foreground py-4">
                                    Bugün için planlanmış görev bulunmuyor.
                                </p>
                            ) : (
                                <div className="space-y-3">
                                    {todayAssignments.map((assignment) => (
                                        <div
                                            key={assignment.id}
                                            className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                                        >
                                            <div className="flex items-center gap-4">
                                                <div className="flex flex-col items-center justify-center w-16 h-16 rounded-lg bg-primary/10">
                                                    <span className="text-lg font-bold text-primary">
                                                        {format(parseISO(assignment.pickupTime), "HH:mm")}
                                                    </span>
                                                </div>
                                                <div>
                                                    <div className="font-medium">
                                                        {assignment.vehicle?.name || "Araç Atanmadı"}
                                                        {assignment.vehicle?.plateNumber && (
                                                            <span className="text-muted-foreground ml-2">
                                                                ({assignment.vehicle.plateNumber})
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                                        <span className="flex items-center gap-1">
                                                            <Users className="h-3 w-3" />
                                                            {assignment.studentCount} öğrenci
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Clock className="h-3 w-3" />
                                                            ~{Math.round(
                                                                (new Date(assignment.estimatedDropoffTime).getTime() -
                                                                    new Date(assignment.pickupTime).getTime()) / 60000
                                                            )} dk
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                {getStatusBadge(assignment.status)}
                                                <Link href={`/driver/assignments/${assignment.id}`}>
                                                    <Button variant="ghost" size="icon">
                                                        <ChevronRight className="h-5 w-5" />
                                                    </Button>
                                                </Link>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Completed Today */}
                    {completedToday.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-lg">
                                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                                    Bugün Tamamlanan
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-2">
                                    {completedToday.map((assignment) => (
                                        <div
                                            key={assignment.id}
                                            className="flex items-center justify-between p-3 rounded-lg border opacity-75"
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className="text-sm font-medium">
                                                    {format(parseISO(assignment.pickupTime), "HH:mm")}
                                                </span>
                                                <span className="text-sm text-muted-foreground">
                                                    {assignment.vehicle?.name} • {assignment.studentCount} öğrenci
                                                </span>
                                            </div>
                                            {getStatusBadge(assignment.status)}
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Upcoming Assignments */}
                    {upcomingAssignments.length > 0 && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-lg">
                                    <Calendar className="h-5 w-5" />
                                    Yaklaşan Görevler
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-2">
                                    {upcomingAssignments.slice(0, 5).map((assignment) => (
                                        <div
                                            key={assignment.id}
                                            className="flex items-center justify-between p-3 rounded-lg border"
                                        >
                                            <div className="flex items-center gap-3">
                                                <Badge variant="outline">
                                                    {getDateLabel(assignment.date)}
                                                </Badge>
                                                <span className="text-sm font-medium">
                                                    {format(parseISO(assignment.pickupTime), "HH:mm")}
                                                </span>
                                                <span className="text-sm text-muted-foreground">
                                                    {assignment.vehicle?.name} • {assignment.studentCount} öğrenci
                                                </span>
                                            </div>
                                            <Link href={`/driver/assignments/${assignment.id}`}>
                                                <Button variant="ghost" size="sm">
                                                    Detay
                                                </Button>
                                            </Link>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Empty State */}
                    {assignments.length === 0 && (
                        <Card>
                            <CardContent className="py-12 text-center">
                                <Route className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                                <h3 className="text-lg font-medium mb-2">Henüz görev atanmamış</h3>
                                <p className="text-muted-foreground">
                                    Size atanmış servis görevi bulunmuyor. Yönetici tarafından görev atandığında burada görünecektir.
                                </p>
                            </CardContent>
                        </Card>
                    )}
                </>
            )}
        </div>
    );
}
