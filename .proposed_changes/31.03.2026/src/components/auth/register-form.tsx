
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { UserPlus, Hash } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";
import React, { useState } from "react";
import { register } from "@/lib/supabase-auth";
import type { DbUser } from "@/types/db";

const registerFormSchema = z.object({
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  studentNumber: z.string().regex(/^\d{12}$/, { message: "Öğrenci numarası 12 haneli bir sayı olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." })
    .refine(email => email.endsWith(".edu.tr") || email.endsWith(".edu"), {
      message: "Lütfen geçerli bir okul e-posta adresi girin (örn: kullanici@okul.edu.tr)."
    }),
  password: z.string().min(6, { message: "Şifre en az 6 karakter olmalıdır." }),
  confirmPassword: z.string().min(6, { message: "Şifre tekrarı en az 6 karakter olmalıdır." }),
  passwordHint: z.string().min(2, { message: "Lütfen şifrenizi hatırlamak için bir ipucu girin." }).optional().or(z.literal('')),
}).refine(data => data.password === data.confirmPassword, {
  message: "Şifreler eşleşmiyor.",
  path: ["confirmPassword"],
});

type RegisterFormValues = z.infer<typeof registerFormSchema>;

export default function RegisterForm() {
  const { toast } = useToast();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerFormSchema),
    defaultValues: {
      name: "",
      studentNumber: "",
      email: "",
      password: "",
      confirmPassword: "",
      passwordHint: "",
    },
  });

  async function onSubmit(data: RegisterFormValues) {
    setIsLoading(true);

    try {
      // Prepare user data for Supabase registration
      const newUserPayload: Omit<DbUser, 'id' | 'email' | 'createdAt' | 'updatedAt' | 'passwordHash' | 'weeklyScheduleId'> = {
        name: data.name,
        studentNumber: data.studentNumber,
        role: "student", // All registrations are students
        passwordHint: data.passwordHint,
        homeAddress: "",
        accessibilityNeeds: [],
      };

      // Register user with Supabase Auth and create Db document
      // The register function automatically creates the weekly schedule
      const createdUser = await register(data.email, data.password, newUserPayload);

      toast({
        title: "Kayıt Başarılı",
        description: `Hesabınız başarıyla oluşturuldu: ${createdUser.name}. Giriş sayfasına yönlendiriliyorsunuz.`,
      });
      router.push("/login");
    } catch (error: any) {
      console.error("Registration error:", error);
      toast({
        title: "Kayıt Başarısız",
        description: error.message || "Kullanıcı oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
          name="studentNumber"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Öğrenci Numarası</FormLabel>
              <FormControl>
                <Input placeholder="Örn: 202003002016" {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <Hash className="h-4 w-4" /> 12 haneli okul numaranız.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Okul E-posta Adresi</FormLabel>
              <FormControl>
                <Input type="email" placeholder="ornek@okul.edu.tr" {...field} />
              </FormControl>
              <FormDescription>
                Lütfen geçerli okul e-posta adresinizi girin.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Şifre</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
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
              <FormLabel>Şifre Tekrarı</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
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
              <FormLabel>Şifre İpucu (İsteğe Bağlı)</FormLabel>
              <FormControl>
                <Input placeholder="Örn: İlk evcil hayvanımın adı" {...field} />
              </FormControl>
              <FormDescription>
                Şifrenizi unutursanız size gösterilecek bir hatırlatıcı.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Kayıt Olunuyor..." : "Kayıt Ol"}
          {!isLoading && <UserPlus className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
