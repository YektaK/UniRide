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
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { updatePassword } from "@/lib/supabase-auth";
import { useState, useEffect } from "react";
import { Lock, CheckCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { getSupabaseClient } from "@/lib/supabase";
import { useTranslations } from "next-intl";

export default function ResetPasswordPage() {
    const t = useTranslations("page.auth.resetPassword");
    const tc = useTranslations("common");
    const { toast } = useToast();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [hasSessionError, setHasSessionError] = useState(false);

    const resetPasswordSchema = z.object({
        password: z.string().min(6, { message: t("minLengthError") }),
        confirmPassword: z.string().min(6, { message: t("minLengthError") }),
    }).refine((data) => data.password === data.confirmPassword, {
        message: t("mismatchError"),
        path: ["confirmPassword"],
    });

    type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

    useEffect(() => {
        const checkSession = async () => {
            try {
                const supabase = getSupabaseClient();
                const { data, error } = await supabase.auth.getSession();

                if (error || !data.session) {
                    console.warn("No active session found. The reset link may be invalid or expired.");
                }
            } catch (err) {
                console.error("Session check error", err);
            }
        };
        checkSession();
    }, []);

    const form = useForm<ResetPasswordValues>({
        resolver: zodResolver(resetPasswordSchema),
        defaultValues: {
            password: "",
            confirmPassword: "",
        },
    });

    async function onSubmit(data: ResetPasswordValues) {
        setIsLoading(true);
        try {
            await updatePassword(data.password);
            setIsSuccess(true);
            toast({
                title: t("successTitle"),
                description: t("successDesc"),
            });
            setTimeout(() => {
                router.push("/login");
            }, 3000);
        } catch (error: any) {
            toast({
                title: t("failedTitle"),
                description: error.message || t("failedDesc"),
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-background">
            <Card className="w-full max-w-md shadow-xl">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold text-primary">{t("title")}</CardTitle>
                    <CardDescription>
                        Please enter a new password for your account.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!isSuccess ? (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="password"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>New Password</FormLabel>
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
                                            <FormLabel>Confirm New Password</FormLabel>
                                            <FormControl>
                                                <Input type="password" placeholder="••••••••" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading ? t("updating") : t("submit")}
                                    {!isLoading && <Lock className="ml-2 h-4 w-4" />}
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center p-4 bg-green-50 text-green-800 rounded-lg dark:bg-green-900/20 dark:text-green-400">
                            <CheckCircle className="mx-auto h-8 w-8 mb-2" />
                            <h3 className="font-semibold text-lg mb-1">{tc("success")}</h3>
                            <p className="text-sm">
                                Password updated. Redirecting to sign in...
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </main>
    );
}
