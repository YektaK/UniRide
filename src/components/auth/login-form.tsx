
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useTranslations } from "next-intl";

export default function LoginForm() {
  const t = useTranslations("component.authLoginForm");
  const tc = useTranslations("common");
  const { login, isLoading } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const loginFormSchema = z.object({
    emailOrUsername: z.string().min(1, { message: "Please enter your email or username." }),
    password: z.string().min(1, { message: "Please enter your password." }),
  });

  type LoginFormValues = z.infer<typeof loginFormSchema>;

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      emailOrUsername: "",
      password: "",
    },
  });

  async function fetchHint() {
    const emailOrNum = form.getValues().emailOrUsername;
    if (!emailOrNum) {
      toast({
        title: "Information Missing",
        description: "Please enter your email or student number to see the hint.",
        variant: "destructive",
      });
      return;
    }

    try {
      const res = await fetch("/api/auth/hint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emailOrStudentNumber: emailOrNum }),
      });
      const data = await res.json();

      toast({
        title: "\uD83D\uDCA1 Password Hint",
        description: data.hint || "No custom hint found.",
      });
    } catch (e) {
      toast({
        title: tc("error"),
        description: "Could not fetch hint.",
        variant: "destructive",
      });
    }
  }

  async function onSubmit(data: LoginFormValues) {
    try {
      await login(data.emailOrUsername, data.password);
      toast({
        title: t("successTitle"),
        description: "Redirecting to dashboard...",
      });
      router.push("/dashboard");
    } catch (error: any) {
      toast({
        title: t("failedTitle"),
        description: error.message || t("failedDesc"),
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="emailOrUsername"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email or Username</FormLabel>
              <FormControl>
                <Input placeholder="example@uniride.com or your_username" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <div className="flex items-center justify-between">
                <FormLabel>Password</FormLabel>
                <Link
                  href="/forgot-password"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <div className="flex justify-between items-center mt-1">
                <FormMessage />
                <button
                  type="button"
                  onClick={fetchHint}
                  className="text-xs text-muted-foreground hover:text-primary transition-colors"
                >
                  Show password hint
                </button>
              </div>
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? t("signingIn") : t("submit")}
          {!isLoading && <LogIn className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
