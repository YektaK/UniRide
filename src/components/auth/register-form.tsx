
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
import { useTranslations } from "next-intl";

export default function RegisterForm() {
  const t = useTranslations("component.authRegisterForm");
  const tc = useTranslations("common");
  const { toast } = useToast();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const registerFormSchema = z.object({
    name: z.string().min(2, { message: "Name must be at least 2 characters." }),
    studentNumber: z.string().regex(/^\d{12}$/, { message: t("studentNoError") }),
    email: z.string().email({ message: "Please enter a valid email address." })
      .refine(email => email.endsWith(".edu.tr") || email.endsWith(".edu"), {
        message: "Please enter a valid school email address (e.g. user@school.edu.tr).",
      }),
    password: z.string().min(6, { message: t("passwordMinError") }),
    confirmPassword: z.string().min(6, { message: t("passwordRepeatError") }),
    passwordHint: z.string().min(2, { message: "Please enter a password hint." }).optional().or(z.literal("")),
  }).refine(data => data.password === data.confirmPassword, {
    message: t("passwordMismatch"),
    path: ["confirmPassword"],
  });

  type RegisterFormValues = z.infer<typeof registerFormSchema>;

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
      const newUserPayload: Omit<DbUser, "id" | "email" | "createdAt" | "updatedAt" | "passwordHash" | "weeklyScheduleId"> = {
        name: data.name,
        studentNumber: data.studentNumber,
        role: "student",
        passwordHint: data.passwordHint,
        homeAddress: "",
        accessibilityNeeds: [],
      };

      const createdUser = await register(data.email, data.password, newUserPayload);

      toast({
        title: tc("success"),
        description: `Account created: ${createdUser.name}. Redirecting to sign in.`,
      });
      router.push("/login");
    } catch (error: any) {
      console.error("Registration error:", error);
      toast({
        title: tc("error"),
        description: error.message || "An error occurred while creating the account. Please try again.",
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
              <FormLabel>Full Name</FormLabel>
              <FormControl>
                <Input placeholder={t("namePlaceholder")} {...field} />
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
              <FormLabel>Student Number</FormLabel>
              <FormControl>
                <Input placeholder={t("studentNoPlaceholder")} {...field} />
              </FormControl>
              <FormDescription className="flex items-center gap-1">
                <Hash className="h-4 w-4" /> 12-digit school number.
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
              <FormLabel>School Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="example@school.edu.tr" {...field} />
              </FormControl>
              <FormDescription>
                Please enter your valid school email address.
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
              <FormLabel>Password</FormLabel>
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
              <FormLabel>Confirm Password</FormLabel>
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
              <FormLabel>Password Hint (Optional)</FormLabel>
              <FormControl>
                <Input placeholder={t("hintPlaceholder")} {...field} />
              </FormControl>
              <FormDescription>
                A reminder shown if you forget your password.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? t("signingUp") : t("submit")}
          {!isLoading && <UserPlus className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
