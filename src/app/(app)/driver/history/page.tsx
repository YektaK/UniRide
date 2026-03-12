"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { format, parseISO } from "date-fns";
import { tr } from "date-fns/locale";
import {
    History,
    Clock,
    Users,
    CheckCircle2,
    XCircle
} from "lucide-react";
import { adminApi } from "@/lib/admin-api";
import type { RouteAssignment } from "@/types/db";
import type { Vehicle } from "@/types";

interface AssignmentWithDetails extends RouteAssignment {
    vehicle?: Vehicle;
    studentCount: number;
}

export default function DriverHistoryPage() {
    const { user } = useAuth();
    const { toast } = useToast();
    const [assignments, setAssignments] = useState<AssignmentWithDetails[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user?.id) {
            loadHistory();
        }
    }, [user?.id]);

    const loadHistory = async () => {
        try {
            setLoading(true);

            const [assignmentsData, vehiclesData] = await Promise.all([
                fetch("/api/driver/assignments").then(res => res.json()).catch(() => []),
                adminApi.vehicles.getAll().catch(() => [])
            ]);

            const completedAssignments: AssignmentWithDetails[] = (assignmentsData || [])
                .filter((a: RouteAssignment) =>
                    a.driverId === user?.id &&
                    (a.status === "completed" || a.status === "cancelled")
                )
                .map((assignment: RouteAssignment) => ({
                    ...assignment,
                    vehicle: vehiclesData.find((v: Vehicle) => v.id === assignment.vehicleId),
                    studentCount: assignment.studentIds?.length || 0
                }))
                .sort((a: AssignmentWithDetails, b: AssignmentWithDetails) =>
                    new Date(b.pickupTime).getTime() - new Date(a.pickupTime).getTime()
                );

            setAssignments(completedAssignments);
        } catch (error: any) {
            console.error("Error loading history:", error);
            toast({
                title: "Yükleme Hatası",
                description: "Geçmiş seferler yüklenirken bir hata oluştu.",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

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

    const completedCount = assignments.filter(a => a.status === "completed").length;
    const cancelledCount = assignments.filter(a => a.status === "cancelled").length;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold flex items-center gap-2">
                    <History className="text-primary" />
                    Geçmiş Seferler
                </h1>
                <p className="text-muted-foreground">
                    Tamamlanan ve iptal edilen servis görevleriniz
                </p>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Tamamlanan</CardTitle>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">{completedCount}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">İptal Edilen</CardTitle>
                        <XCircle className="h-4 w-4 text-red-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-600">{cancelledCount}</div>
                    </CardContent>
                </Card>
            </div>

            {/* History List */}
            <Card>
                <CardHeader>
                    <CardTitle>Sefer Geçmişi</CardTitle>
                    <CardDescription>
                        Son {assignments.length} sefer
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <p className="text-center text-muted-foreground py-8">Yükleniyor...</p>
                    ) : assignments.length === 0 ? (
                        <p className="text-center text-muted-foreground py-8">
                            Henüz tamamlanmış sefer bulunmuyor.
                        </p>
                    ) : (
                        <div className="space-y-3">
                            {assignments.map((assignment) => (
                                <div
                                    key={assignment.id}
                                    className="flex items-center justify-between p-4 rounded-lg border"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="text-sm">
                                            <div className="font-medium">
                                                {format(parseISO(assignment.date), "dd MMMM yyyy", { locale: tr })}
                                            </div>
                                            <div className="text-muted-foreground flex items-center gap-2">
                                                <Clock className="h-3 w-3" />
                                                {format(parseISO(assignment.pickupTime), "HH:mm")}
                                            </div>
                                        </div>
                                        <div className="text-sm">
                                            <div>{assignment.vehicle?.name || "Araç Bilinmiyor"}</div>
                                            <div className="text-muted-foreground flex items-center gap-1">
                                                <Users className="h-3 w-3" />
                                                {assignment.studentCount} öğrenci
                                            </div>
                                        </div>
                                    </div>
                                    <Badge
                                        variant={assignment.status === "completed" ? "outline" : "destructive"}
                                        className="flex items-center gap-1"
                                    >
                                        {assignment.status === "completed" ? (
                                            <><CheckCircle2 className="h-3 w-3" /> Tamamlandı</>
                                        ) : (
                                            <><XCircle className="h-3 w-3" /> İptal</>
                                        )}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
