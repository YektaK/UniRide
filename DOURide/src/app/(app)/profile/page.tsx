
"use client";

import ProfileForm from "@/components/student/profile-form";
import { useAuth } from "@/hooks/use-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { UserCog } from "lucide-react";

export default function ProfilePage() {
  const { user, isLoading, setUser } = useAuth();

  if (isLoading) {
    return <Card><CardHeader><CardTitle>Yükleniyor...</CardTitle></CardHeader><CardContent><p>Profil bilgileriniz yükleniyor.</p></CardContent></Card>;
  }

  if (!user) {
    return <Card><CardHeader><CardTitle>Hata</CardTitle></CardHeader><CardContent><p>Kullanıcı bulunamadı. Lütfen tekrar giriş yapın.</p></CardContent></Card>;
  }

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl flex items-center gap-2"><UserCog className="text-primary"/>Profil Bilgilerim</CardTitle>
          <CardDescription>
            Kişisel bilgilerinizi, adresinizi ve erişilebilirlik tercihlerinizi buradan yönetebilirsiniz.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ProfileForm currentUser={user} onUpdateProfile={setUser} />
        </CardContent>
      </Card>
    </div>
  );
}
