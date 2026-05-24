
"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from 'next-intl';
import type { RideRequest, RideStatus, User } from "@/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ShieldAlert, CheckCircle, XCircle, AlertCircle, Search } from "lucide-react";
import { format } from "date-fns";
import { tr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";
import { adminApi } from "@/lib/admin-api";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const statusDisplayMap: Record<RideStatus, { labelKey: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }> = {
  pending_student_confirmation: { labelKey: "status.waitingStudent", variant: "outline", className: "border-yellow-500 text-yellow-700" },
  confirmed: { labelKey: "status.confirmed", variant: "default", className: "bg-green-600 hover:bg-green-700 text-white" },
  cancelled_by_student: { labelKey: "status.studentCancelled", variant: "destructive" },
  cancelled_by_admin: { labelKey: "status.adminCancelled", variant: "destructive", className: "bg-red-700 text-white" },
  in_progress: { labelKey: "status.enRoute", variant: "default", className: "bg-blue-500 hover:bg-blue-600 text-white" },
  completed: { labelKey: "status.completedTrip", variant: "secondary", className: "bg-gray-500 text-white" },
  pending_admin_approval: { labelKey: "status.waitingAdmin", variant: "outline", className: "border-orange-500 text-orange-700" },
};

export default function AdminRideRequestsPage() {
  const t = useTranslations('page.admin.rideRequests');
  const tc = useTranslations('common');
  const { toast } = useToast();
  const [allRequests, setAllRequests] = useState<RideRequest[]>([]);
  const [filteredRequests, setFilteredRequests] = useState<RideRequest[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    setIsLoading(true);
    const loadData = async () => {
      try {
        // Load users and ride requests via admin API
        const [fetchedUsers, fetchedRequests] = await Promise.all([
          adminApi.users.getAll(),
          adminApi.rideRequests.getAll(),
        ]);

        // Convert users from snake_case
        const convertedUsers = fetchedUsers.map((u: any) => ({
          id: u.id,
          name: u.name,
          email: u.email,
          role: u.role,
          studentNumber: u.student_number,
        }));

        // Convert ride requests from snake_case
        const convertedRequests = fetchedRequests.map((r: any) => ({
          id: r.id,
          userId: r.user_id,
          type: r.type,
          pickupLocation: r.pickup_location || { address: "Belirtilmemiş", lat: 0, lng: 0 },
          dropoffLocation: r.dropoff_location || { address: "Belirtilmemiş", lat: 0, lng: 0 },
          requestedPickupTime: r.requested_pickup_time,
          status: r.status,
          createdAt: r.created_at,
          updatedAt: r.updated_at,
        }));

        setUsers(convertedUsers);
        setAllRequests(convertedRequests);
        setFilteredRequests(convertedRequests);
      } catch (error) {
        console.error("Error loading data:", error);
        toast({
          title: tc('error'),
          description: tc('error'),
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    const lowerSearchTerm = searchTerm.toLowerCase();
    const filtered = allRequests.filter(request => {
      const student = users.find(u => u.id === request.userId);
      const studentName = student?.name.toLowerCase() || "";
      const requestDate = format(new Date(request.requestedPickupTime), "dd MMMM yyyy HH:mm", { locale: tr }).toLowerCase();
      const statusLabel = tc(statusDisplayMap[request.status].labelKey).toLowerCase();
      const pickupLocation = request.pickupLocation.address.toLowerCase();

      return studentName.includes(lowerSearchTerm) ||
        requestDate.includes(lowerSearchTerm) ||
        statusLabel.includes(lowerSearchTerm) ||
        pickupLocation.includes(lowerSearchTerm);
    });
    setFilteredRequests(filtered);
  }, [searchTerm, allRequests, users]);


  const handleUpdateRequestStatus = async (requestId: string, newStatus: RideStatus, studentName: string | undefined) => {
    try {
      await adminApi.rideRequests.updateStatus(requestId, { status: newStatus });

      setAllRequests(prevRequests =>
        prevRequests.map(req =>
          req.id === requestId ? { ...req, status: newStatus } : req
        )
      );
      setFilteredRequests(prevRequests =>
        prevRequests.map(req =>
          req.id === requestId ? { ...req, status: newStatus } : req
        )
      );
      toast({
        title: tc('success'),
        description: `${studentName || tc('select')} - ${tc(statusDisplayMap[newStatus].labelKey)}`,
      });
    } catch (error) {
      console.error("Error updating request status:", error);
      toast({
        title: tc('error'),
        description: t('description'),
        variant: "destructive",
      });
    }
  };

  const getStudentName = (userId: string): string => {
    const user = users.find(u => u.id === userId);
    return user ? user.name : tc('select');
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader><CardTitle>{tc('loading')}</CardTitle></CardHeader>
        <CardContent><p>{tc('loading')}</p></CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><ShieldAlert className="text-primary" />{tc('details')}</CardTitle>
          <CardDescription>
            {t('description')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder={t('searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 w-full md:w-1/2 lg:w-1/3"
              />
            </div>
          </div>

          {allRequests.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <ShieldAlert className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{tc('noResults')}</p>
            </div>
          ) : filteredRequests.length === 0 ? (
            <div className="my-6 p-4 border border-dashed rounded-lg aspect-video bg-muted flex flex-col items-center justify-center">
              <Search className="h-16 w-16 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{tc('noResults')}</p>
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{tc('select')}</TableHead>
                    <TableHead>Talep Tarihi</TableHead>
                    <TableHead>Tip</TableHead>
                    <TableHead>Alınış Yeri</TableHead>
                    <TableHead>Bırakılış Yeri</TableHead>
                    <TableHead className="text-center">{tc('status.completed')}</TableHead>
                    <TableHead className="text-right">{tc('details')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRequests.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).map((request) => {
                    const studentName = getStudentName(request.userId);
                    return (
                      <TableRow key={request.id}>
                        <TableCell className="font-medium">{studentName}</TableCell>
                        <TableCell>
                          {format(new Date(request.requestedPickupTime), "dd MMM yy, HH:mm", { locale: tr })}
                        </TableCell>
                        <TableCell>
                          <Badge variant={request.type === "adhoc" ? "secondary" : "outline"}>
                            {request.type === "adhoc" ? tc('selectAll') : tc('filter')}
                          </Badge>
                        </TableCell>
                        <TableCell>{request.pickupLocation.address}</TableCell>
                        <TableCell>{request.dropoffLocation.address}</TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant={statusDisplayMap[request.status].variant}
                            className={cn("font-semibold", statusDisplayMap[request.status].className)}
                          >
                            {tc(statusDisplayMap[request.status].labelKey)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right space-x-2">
                          {request.status === "pending_admin_approval" && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleUpdateRequestStatus(request.id, "confirmed", studentName)}
                                className="text-green-600 border-green-600 hover:bg-green-50 hover:text-green-700"
                              >
                                <CheckCircle className="mr-1 h-4 w-4" /> {tc('confirm')}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleUpdateRequestStatus(request.id, "cancelled_by_admin", studentName)}
                                className="text-red-600 border-red-600 hover:bg-red-50 hover:text-red-700"
                              >
                                <XCircle className="mr-1 h-4 w-4" /> {tc('cancel')}
                              </Button>
                            </>
                          )}
                          {(request.status === "confirmed" || request.status === "in_progress") && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUpdateRequestStatus(request.id, "cancelled_by_admin", studentName)}
                              className="text-red-600 border-red-600 hover:bg-red-50 hover:text-red-700"
                            >
                              <XCircle className="mr-1 h-4 w-4" /> {tc('cancel')}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

