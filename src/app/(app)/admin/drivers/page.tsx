"use client";

import { useEffect, useState } from "react";
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { format, parseISO } from "date-fns";
import { tr } from "date-fns/locale";
import { Download, FileText, Calendar, MapPin, Users, Clock } from "lucide-react";
import { getAllRouteAssignments, getAllVehicles, getAllUsers } from "@/lib/database";
import type { RouteAssignment } from "@/types/db";
import type { Vehicle } from "@/types";
import type { DbUser } from "@/types/db";
import { exportDriverAssignmentsToExcel, exportDriverAssignmentsToPDF } from "@/services/excel/driver-export";

export default function DriverAssignmentsPage() {
  const t = useTranslations('page.admin.driverAssignments');
  const tc = useTranslations('common');
  const [assignments, setAssignments] = useState<RouteAssignment[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [users, setUsers] = useState<DbUser[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(
    format(new Date(), "yyyy-MM-dd")
  );
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      const [assignmentsData, vehiclesData, usersData] = await Promise.all([
        getAllRouteAssignments({ date: selectedDate }),
        getAllVehicles(),
        getAllUsers(),
      ]);
      setAssignments(assignmentsData);
      setVehicles(vehiclesData);
      setUsers(usersData);
    } catch (error: any) {
      toast({
        title: tc('error'),
        description: error.message || tc('error'),
        variant: "destructive",
      });
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount initial data load; loading flag flips synchronously. Upstream fix: data-fetching framework.
    loadData();
  }, [selectedDate]);

  const getVehicle = (vehicleId: string) => {
    return vehicles.find((v) => v.id === vehicleId);
  };

  const getDriver = (driverId?: string) => {
    if (!driverId) return null;
    return users.find((u) => u.id === driverId && u.role === "driver");
  };

  const getStudents = (studentIds: string[]) => {
    return users.filter((u) => studentIds.includes(u.id) && u.role === "student");
  };

  const handleExportExcel = async () => {
    try {
      const assignmentsWithDetails = assignments.map((assignment) => ({
        assignment,
        vehicle: getVehicle(assignment.vehicleId),
        driver: getDriver(assignment.driverId),
        students: getStudents(assignment.studentIds),
      }));

      await exportDriverAssignmentsToExcel(assignmentsWithDetails, selectedDate);
      toast({
        title: tc('success'),
        description: tc('success'),
      });
    } catch (error: any) {
      toast({
        title: tc('error'),
        description: error.message || tc('error'),
        variant: "destructive",
      });
      console.error("Error exporting to Excel:", error);
    }
  };

  const handleExportPDF = async () => {
    try {
      const assignmentsWithDetails = assignments.map((assignment) => ({
        assignment,
        vehicle: getVehicle(assignment.vehicleId),
        driver: getDriver(assignment.driverId),
        students: getStudents(assignment.studentIds),
      }));

      await exportDriverAssignmentsToPDF(assignmentsWithDetails, selectedDate);
      toast({
        title: tc('success'),
        description: tc('success'),
      });
    } catch (error: any) {
      toast({
        title: tc('error'),
        description: error.message || tc('error'),
        variant: "destructive",
      });
      console.error("Error exporting to PDF:", error);
    }
  };

  const getStatusBadge = (status: RouteAssignment["status"]) => {
    const variants: Record<RouteAssignment["status"], "default" | "secondary" | "destructive" | "outline"> = {
      scheduled: "default",
      in_progress: "secondary",
      completed: "outline",
      cancelled: "destructive",
    };
    const labels: Record<RouteAssignment["status"], string> = {
      scheduled: tc('status.planned'),
      in_progress: tc('status.inProgress'),
      completed: tc('status.completed'),
      cancelled: tc('status.cancelled'),
    };
    return (
      <Badge variant={variants[status]}>
        {labels[status]}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <Users className="text-primary" />
                {tc('sidebar.driverAssignments')}
              </CardTitle>
              <CardDescription>
                {tc('sidebar.driverAssignments')}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border rounded-md"
              />
              <Button onClick={handleExportExcel} variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Excel
              </Button>
              <Button onClick={handleExportPDF} variant="outline">
                <FileText className="mr-2 h-4 w-4" />
                PDF
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">{tc('loading')}</div>
          ) : assignments.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {tc('noResults')}
            </div>
          ) : (
            <div className="space-y-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Araç</TableHead>
                    <TableHead>{tc('select')}</TableHead>
                    <TableHead>Alış Saati</TableHead>
                    <TableHead>Tahmini Varış</TableHead>
                    <TableHead>Öğrenci Sayısı</TableHead>
                    <TableHead>{tc('status.completed')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assignments.map((assignment) => {
                    const vehicle = getVehicle(assignment.vehicleId);
                    const driver = getDriver(assignment.driverId);
                    const students = getStudents(assignment.studentIds);

                    return (
                      <TableRow key={assignment.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">
                              {vehicle?.name || t('noVehicle')}
                            </span>
                            {vehicle?.plateNumber && (
                              <Badge variant="outline" className="text-xs">
                                {vehicle.plateNumber}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {driver ? (
                            <span className="font-medium">{driver.name}</span>
                          ) : (
                            <span className="text-muted-foreground">{t('noVehicle')}</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-muted-foreground" />
                            {format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr })}
                          </div>
                        </TableCell>
                        <TableCell>
                          {format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr })}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-muted-foreground" />
                            {students.length} {tc('select')}
                          </div>
                        </TableCell>
                        <TableCell>{getStatusBadge(assignment.status)}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              {/* Detailed view for each assignment */}
              <div className="space-y-4 mt-6">
                {assignments.map((assignment) => {
                  const vehicle = getVehicle(assignment.vehicleId);
                  const driver = getDriver(assignment.driverId);
                  const students = getStudents(assignment.studentIds);

                  return (
                    <Card key={assignment.id} className="border-l-4 border-l-primary">
                      <CardHeader className="pb-3">
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle className="text-lg">
                              {vehicle?.name || t('noVehicle')}
                              {vehicle?.plateNumber && ` (${vehicle.plateNumber})`}
                            </CardTitle>
                            <CardDescription>
                              {driver ? `${tc('select')}: ${driver.name}` : t('noVehicle')}
                            </CardDescription>
                          </div>
                          {getStatusBadge(assignment.status)}
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <div className="text-sm text-muted-foreground flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {tc('filter')}
                            </div>
                            <div className="font-medium">
                              {format(parseISO(assignment.date), "dd MMMM yyyy", { locale: tr })}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {tc('details')}
                            </div>
                            <div className="font-medium">
                              {format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr })}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">{tc('details')}</div>
                            <div className="font-medium">
                              {format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr })}
                            </div>
                          </div>
                          <div>
                            <div className="text-sm text-muted-foreground">{tc('configuration')}</div>
                            <div className="font-medium">
                              {students.length} / {vehicle ? vehicle.seatingCapacity + vehicle.wheelchairCapacity : "-"}
                            </div>
                          </div>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground mb-2">{tc('select')}:</div>
                          <div className="flex flex-wrap gap-2">
                            {students.map((student) => (
                              <Badge key={student.id} variant="outline">
                                {student.name}
                                {student.studentNumber && ` (${student.studentNumber})`}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

