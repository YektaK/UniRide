
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";
import {
  LayoutDashboard,
  CalendarDays,
  ClipboardList,
  User,
  Bus,
  Users,
  Settings,
  MapPin,
  ShieldAlert,
  LogOut,
  HelpingHand,
  ListChecks,
  FilePenLine,
  BarChartHorizontal,
  Navigation,
  Route,
  Cpu,
  FlaskConical,
  BarChart3,
} from "lucide-react";
import { Button } from "../ui/button";

const commonMenuItems = [
  { href: "/dashboard", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/profile", labelKey: "profile", icon: User },
];

const studentMenuItems = [
  { href: "/schedule", labelKey: "mySchedule", icon: CalendarDays },
  { href: "/request-ride", labelKey: "rideRequest", icon: ClipboardList },
  { href: "/ride-history", labelKey: "myRequests", icon: ListChecks },
  { href: "/track-ride", labelKey: "trackRide", icon: MapPin },
];

const adminMenuItems = [
  { href: "/admin/vehicles", labelKey: "vehicleManagement", icon: Bus },
  { href: "/admin/users", labelKey: "userManagement", icon: Users },
  { href: "/admin/schedules", labelKey: "schedules", icon: FilePenLine },
  { href: "/admin/ride-requests", labelKey: "rideRequests", icon: ShieldAlert },
  { href: "/admin/drivers", labelKey: "driverAssignments", icon: Users },
  { href: "/admin/vehicle-planning", labelKey: "vehiclePlanning", icon: Route },
  { href: "/admin/sandbox", labelKey: "sandbox", icon: FlaskConical },
  { href: "/admin/compare", labelKey: "algorithmCompare", icon: Cpu },
  { href: "/admin/benchmark", labelKey: "benchmarkSuite", icon: BarChart3 },
  { href: "/admin/route-test", labelKey: "routeTest", icon: Navigation },
  { href: "/admin/reports", labelKey: "reports", icon: BarChartHorizontal },
  { href: "/admin/settings", labelKey: "settings", icon: Settings },
];

const driverMenuItems = [
  { href: "/driver/assignments", labelKey: "myTasks", icon: Route },
  { href: "/driver/navigation", labelKey: "navigation", icon: Navigation },
  { href: "/driver/history", labelKey: "pastTrips", icon: ListChecks },
];

export default function AppSidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const t = useTranslations("common.sidebar");

  if (!user) return null;

  const getMenuItems = () => {
    switch (user.role) {
      case "admin":
        return [...commonMenuItems, ...adminMenuItems];
      case "driver":
        return [...commonMenuItems, ...driverMenuItems];
      default:
        return [...commonMenuItems, ...studentMenuItems];
    }
  };

  const menuItems = getMenuItems();

  return (
    <Sidebar collapsible="icon" variant="sidebar" side="left" className="border-r">
      <SidebarHeader className="p-4 justify-center">
        <Link href="/dashboard">
          <div className="flex items-center gap-2 group-data-[collapsible=icon]:hidden">
            <HelpingHand className="h-8 w-8 text-primary" />
            <h1 className="text-lg font-semibold text-foreground">UniRide</h1>
          </div>
          <HelpingHand className="h-8 w-8 text-primary hidden group-data-[collapsible=icon]:block" />
        </Link>
      </SidebarHeader>
      <SidebarContent className="flex-grow p-2">
        <SidebarMenu>
          {menuItems.map((item) => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton
                asChild
                isActive={pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))}
                tooltip={{ children: t(item.labelKey), side: "right", align: "center" }}
                aria-label={t(item.labelKey)}
              >
                <Link href={item.href}>
                  <item.icon />
                  <span>{t(item.labelKey)}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter className="p-4 border-t">
        <Button variant="ghost" onClick={logout} className="w-full justify-start group-data-[collapsible=icon]:justify-center">
          <LogOut className="mr-2 group-data-[collapsible=icon]:mr-0 h-4 w-4" />
          <span className="group-data-[collapsible=icon]:hidden">{t("logout")}</span>
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}

