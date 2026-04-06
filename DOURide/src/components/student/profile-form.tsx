
"use client";

import type { User } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Save, MapPin, Hash, KeyRound, Eye, EyeOff } from "lucide-react";
import { updateUser as dbUpdateUser } from "@/lib/database";
import { getSupabaseClient } from "@/lib/supabase";
import React, { useState } from "react";

interface ProfileFormProps {
  currentUser: User;
  onUpdateProfile: (updatedUser: User) => void;
}

const accessibilityNeedsOptions = [
  { id: "wheelchair", label: "Tekerlekli Sandalye Kullanıcısı" },
  { id: "visual_impairment", label: "Görme Engelli" },
  { id: "hearing_impairment", label: "İşitme Engelli" },
  { id: "other", label: "Diğer (Lütfen belirtin)" },
];

const profileFormSchema = z.object({
  name: z.string().min(2, { message: "İsim en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  studentNumber: z.string().optional(),
  homeAddress: z.string().min(10, { message: "Ev adresi en az 10 karakter olmalıdır." }).optional().or(z.literal("")),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
  // Password change fields (optional — only sent if filled)
  newPassword: z.string().min(6, { message: "Şifre en az 6 karakter olmalıdır." }).optional().or(z.literal("")),
  confirmPassword: z.string().optional().or(z.literal("")),
  passwordHint: z.string().max(100, { message: "Şifre ipucu en fazla 100 karakter olabilir." }).optional().or(z.literal("")),
}).refine((data) => {
  if (data.newPassword && data.newPassword !== data.confirmPassword) {
    return false;
  }
  return true;
}, {
  message: "Şifreler eşleşmiyor.",
  path: ["confirmPassword"],
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

export default function ProfileForm({ currentUser, onUpdateProfile }: ProfileFormProps) {
  const { toast } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      name: currentUser.name || "",
      email: currentUser.email || "",
      studentNumber: currentUser.studentNumber || "",
      homeAddress: currentUser.homeAddress || "",
      accessibilityNeeds: currentUser.accessibilityNeeds || [],
      otherAccessibilityNeed: currentUser.accessibilityNeeds?.includes("other") ? currentUser.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || "" : "",
      newPassword: "",
      confirmPassword: "",
      passwordHint: (currentUser as any).passwordHint || "",
    },
  });

  async function onSubmit(data: ProfileFormValues) {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
      finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    try {
      // 1. Update basic profile in DB
      const updates: Partial<User> = { name: data.name };
      if (currentUser.role === "student") {
        updates.studentNumber = data.studentNumber;
        updates.homeAddress = data.homeAddress;
        updates.accessibilityNeeds = finalAccessibilityNeeds;
      }
      await dbUpdateUser(currentUser.id, updates);

      // 2. Update password and/or hint if provided
      const hasPasswordChange = data.newPassword && data.newPassword.length >= 6;
      const hasHintChange = data.passwordHint !== undefined;

      if (hasPasswordChange || hasHintChange) {
        const supabase = getSupabaseClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        if (!token) throw new Error("Oturum bulunamadı. Lütfen tekrar giriş yapın.");

        const patchBody: any = {};
        if (hasPasswordChange) patchBody.newPassword = data.newPassword;
        if (hasHintChange) patchBody.passwordHint = data.passwordHint;

        const res = await fetch("/api/profile/password", {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify(patchBody),
        });
        const resData = await res.json();
        if (!res.ok) throw new Error(resData.error || "Şifre güncellenemedi.");

        // Clear password fields after save
        form.setValue("newPassword", "");
        form.setValue("confirmPassword", "");
      }

      // 3. Update context
      onUpdateProfile({ ...currentUser, ...updates });

      toast({
        title: "Profil Güncellendi",
        description: "Bilgileriniz başarıyla kaydedildi.",
      });
    } catch (error: any) {
      console.error("Error updating profile:", error);
      toast({
        title: "Güncelleme Başarısız",
        description: error.message || "Profiliniz güncellenirken bir hata oluştu.",
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        {/* ── Basic Info ── */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Ad Soyad</FormLabel>
              <FormControl>
                <Input placeholder="Adınız Soyadınız" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>E-posta Adresi</FormLabel>
              <FormControl>
                <Input type="email" {...field} readOnly disabled />
              </FormControl>
              <FormDescription>E-posta adresiniz değiştirilemez.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* ── Student-only fields ── */}
        {currentUser.role === "student" && (
          <>
            <FormField
              control={form.control}
              name="studentNumber"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Öğrenci Numarası</FormLabel>
                  <FormControl>
                    <Input placeholder="Örn: 202003002016" {...field} />
                  </FormControl>
                  <FormDescription className="flex items-center gap-1">
                    <Hash className="h-4 w-4" /> Öğrenci numaranız.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="homeAddress"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Ev Adresi</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Tam ev adresinizi girin..." {...field} rows={3} />
                  </FormControl>
                  <FormDescription className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" /> Konumunuz servis planlaması için kullanılacaktır.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="accessibilityNeeds"
              render={() => (
                <FormItem>
                  <div className="mb-4">
                    <FormLabel className="text-base">Erişilebilirlik İhtiyaçları</FormLabel>
                    <FormDescription>
                      Size daha iyi hizmet verebilmemiz için lütfen ilgili seçenekleri işaretleyin.
                    </FormDescription>
                  </div>
                  {accessibilityNeedsOptions.map((item) => (
                    <FormField
                      key={item.id}
                      control={form.control}
                      name="accessibilityNeeds"
                      render={({ field }) => (
                        <FormItem key={item.id} className="flex flex-row items-start space-x-3 space-y-0">
                          <FormControl>
                            <Checkbox
                              checked={field.value?.includes(item.id)}
                              onCheckedChange={(checked) => {
                                return checked
                                  ? field.onChange([...(field.value || []), item.id])
                                  : field.onChange(field.value?.filter((v) => v !== item.id));
                              }}
                            />
                          </FormControl>
                          <FormLabel className="font-normal">{item.label}</FormLabel>
                        </FormItem>
                      )}
                    />
                  ))}
                  <FormMessage />
                </FormItem>
              )}
            />
            {form.watch("accessibilityNeeds")?.includes("other") && (
              <FormField
                control={form.control}
                name="otherAccessibilityNeed"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Diğer Erişilebilirlik İhtiyacı</FormLabel>
                    <FormControl>
                      <Input placeholder="Lütfen belirtin..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
          </>
        )}

        {/* ── Password & Hint Section (all roles) ── */}
        <Separator />
        <div>
          <h3 className="text-base font-semibold flex items-center gap-2 mb-1">
            <KeyRound className="h-4 w-4 text-amber-500" /> Şifre ve Güvenlik
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Şifrenizi değiştirmek istemiyorsanız bu alanları boş bırakın.
          </p>
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="newPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Yeni Şifre</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="Yeni şifrenizi girin (min. 6 karakter)"
                        {...field}
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Şifre Tekrar</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showConfirm ? "text" : "password"}
                        placeholder="Şifrenizi tekrar girin"
                        {...field}
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirm(!showConfirm)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        tabIndex={-1}
                      >
                        {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="passwordHint"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Şifre İpucu</FormLabel>
                  <FormControl>
                    <Input placeholder="Şifrenizi hatırlamanıza yardımcı olacak bir ipucu..." {...field} />
                  </FormControl>
                  <FormDescription>
                    Bu ipucu şifrelerinizi unuttuğunuzda size gösterilir. Şifreyi direkt yazmayın.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <Button type="submit" className="w-full sm:w-auto">
          <Save className="mr-2 h-4 w-4" /> Bilgileri Kaydet
        </Button>
      </form>
    </Form>
  );
}
