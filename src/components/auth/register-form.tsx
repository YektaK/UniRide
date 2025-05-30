
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
import { addUser as dbAddUser } from "@/lib/mock-database"; // Import from mock DB
import type { User } from "@/types";

const registerFormSchema = z.object({
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  studentNumber: z.string().regex(/^\d{12}$/, { message: "Öğrenci numarası 12 haneli bir sayı olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." })
    .refine(email => email.endsWith(".edu.tr") || email.endsWith(".edu"), {
      message: "Lütfen geçerli bir okul e-posta adresi girin (örn: kullanici@okul.edu.tr)."
    }),
  password: z.string().min(6, { message: "Şifre en az 6 karakter olmalıdır." }),
  confirmPassword: z.string().min(6, { message: "Şifre tekrarı en az 6 karakter olmalıdır." }),
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
    },
  });

  async function onSubmit(data: RegisterFormValues) {
    setIsLoading(true);
    
    // Prepare user data for adding to the mock database
    // The addUser function in mock-database will assign 'id', 'role', and 'weeklyScheduleId'
    const newUserPayload: Omit<User, 'id' | 'weeklyScheduleId' | 'role'> = {
      name: data.name,
      studentNumber: data.studentNumber,
      email: data.email,
      password: data.password, // In a real app, hash this password on the backend
      // homeAddress and accessibilityNeeds can be empty or prompted later
      homeAddress: "", 
      accessibilityNeeds: [],
    };

    const createdUser = dbAddUser(newUserPayload);

    if (createdUser) {
      toast({
        title: "Kayıt Başarılı",
        description: `Hesabınız başarıyla oluşturuldu: ${createdUser.name}. Giriş sayfasına yönlendiriliyorsunuz.`,
      });
      router.push("/login");
    } else {
      toast({
        title: "Kayıt Başarısız",
        description: "Kullanıcı oluşturulurken bir hata oluştu. Lütfen tekrar deneyin.",
        variant: "destructive",
      });
    }
    setIsLoading(false);
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
                <Hash className="h-4 w-4"/> 12 haneli okul numaranız.
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
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Kayıt Olunuyor..." : "Kayıt Ol"}
          {!isLoading && <UserPlus className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
