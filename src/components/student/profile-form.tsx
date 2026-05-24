
"use client";

import { useTranslations } from "next-intl";
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

const profileFormSchema = z.object({
  name: z.string().min(2, { message: "İsim en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  studentNumber: z.string().optional(),
  homeAddress: z.string().min(10, { message: "Ev adresi en az 10 karakter olmalıdır." }).optional().or(z.literal("")),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
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
  const t = useTranslations("component.profileForm");
  const tc = useTranslations("common");
  const { toast } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const accessibilityNeedsOptions = [
    { id: "wheelchair", label: t("wheelchair") },
    { id: "visual_impairment", label: t("visualImpairment") },
    { id: "hearing_impairment", label: t("hearingImpairment") },
    { id: "other", label: t("otherAccessibility") },
  ];

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
      passwordHint: currentUser.passwordHint || "",
    },
  });

  async function onSubmit(data: ProfileFormValues) {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
      finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    try {
      const updates: Partial<User> = { name: data.name };
      if (currentUser.role === "student") {
        updates.studentNumber = data.studentNumber;
        updates.homeAddress = data.homeAddress;
        updates.accessibilityNeeds = finalAccessibilityNeeds;
      }
      await dbUpdateUser(currentUser.id, updates);

      const hasPasswordChange = data.newPassword && data.newPassword.length >= 6;
      const hasHintChange = data.passwordHint !== undefined;

      if (hasPasswordChange || hasHintChange) {
        const supabase = getSupabaseClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        if (!token) throw new Error(t("sessionNotFound"));

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
        if (!res.ok) throw new Error(resData.error || t("passwordUpdateFailed"));

        form.setValue("newPassword", "");
        form.setValue("confirmPassword", "");
      }

      onUpdateProfile({ ...currentUser, ...updates });

      toast({
        title: t("profileUpdated"),
        description: t("profileUpdatedDesc"),
      });
    } catch (error: any) {
      console.error("Error updating profile:", error);
      toast({
        title: t("updateFailedTitle"),
        description: error.message || t("updateErrorDesc"),
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{t("nameLabel")}</FormLabel>
              <FormControl>
                <Input placeholder={t("namePlaceholder")} {...field} />
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
              <FormLabel>{t("emailLabel")}</FormLabel>
              <FormControl>
                <Input type="email" {...field} readOnly disabled />
              </FormControl>
              <FormDescription>{t("emailNotChangeable")}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {currentUser.role === "student" && (
          <>
            <FormField
              control={form.control}
              name="studentNumber"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("studentNoLabel")}</FormLabel>
                  <FormControl>
                    <Input placeholder={t("studentNoPlaceholder")} {...field} />
                  </FormControl>
                  <FormDescription className="flex items-center gap-1">
                    <Hash className="h-4 w-4" /> {t("studentNoDescription")}
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
                  <FormLabel>{t("addressLabel")}</FormLabel>
                  <FormControl>
                    <Textarea placeholder={t("addressPlaceholder")} {...field} rows={3} />
                  </FormControl>
                  <FormDescription className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" /> {t("addressDescription")}
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
                    <FormLabel className="text-base">{t("accessibilityLabel")}</FormLabel>
                    <FormDescription>
                      {t("accessibilityDescription")}
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
                    <FormLabel>{t("otherAccLabel")}</FormLabel>
                    <FormControl>
                      <Input placeholder={t("otherAccPlaceholder")} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
          </>
        )}

        <Separator />
        <div>
          <h3 className="text-base font-semibold flex items-center gap-2 mb-1">
            <KeyRound className="h-4 w-4 text-amber-500" /> {t("securitySection")}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {t("securityDescription")}
          </p>
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="newPassword"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("newPasswordLabel")}</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder={t("newPasswordPlaceholder")}
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
                  <FormLabel>{t("confirmPasswordLabel")}</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showConfirm ? "text" : "password"}
                        placeholder={t("repeatPasswordPlaceholder")}
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
                  <FormLabel>{t("hintLabel")}</FormLabel>
                  <FormControl>
                    <Input placeholder={t("hintPlaceholder")} {...field} />
                  </FormControl>
                  <FormDescription>
                    {t("hintDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <Button type="submit" className="w-full sm:w-auto">
          <Save className="mr-2 h-4 w-4" /> {t("saveButton")}
        </Button>
      </form>
    </Form>
  );
}
