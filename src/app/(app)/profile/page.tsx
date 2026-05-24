
"use client";

import { useTranslations } from "next-intl";
import ProfileForm from "@/components/student/profile-form";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UserCog } from "lucide-react";

export default function ProfilePage() {
  const t = useTranslations("page.profile");
  const tc = useTranslations("common");
  const { user, isLoading, updateUser } = useAuth();

  if (isLoading) {
    return <Card><CardHeader><CardTitle>{tc("loading")}</CardTitle></CardHeader><CardContent><p>{t("loading")}</p></CardContent></Card>;
  }

  if (!user) {
    return <Card><CardHeader><CardTitle>{tc("error")}</CardTitle></CardHeader><CardContent><p>{t("notFound")}</p></CardContent></Card>;
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><UserCog className="text-primary"/>{t("title")}</CardTitle>
          <CardDescription>
            {t("description")}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileForm currentUser={user} onUpdateProfile={updateUser} />
        </CardContent>
      </Card>
    </div>
  );
}
