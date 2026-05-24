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
import { resetPasswordForEmail } from "@/lib/supabase-auth";
import { useState } from "react";
import { Mail, ArrowLeft, Bug } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Link from "next/link";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    CardFooter,
} from "@/components/ui/card";
import { useTranslations } from "next-intl";

export default function ForgotPasswordPage() {
    const t = useTranslations("page.auth.forgotPassword");
    const tc = useTranslations("common");
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [isSent, setIsSent] = useState(false);
    const isDevResetUiEnabled =
        process.env.NODE_ENV === "development";

    const forgotPasswordSchema = z.object({
        email: z.string().email({ message: t("validEmailError") }),
    });

    type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

    const form = useForm<ForgotPasswordValues>({
        resolver: zodResolver(forgotPasswordSchema),
        defaultValues: {
            email: "",
        },
    });

    async function onSubmit(data: ForgotPasswordValues) {
        setIsLoading(true);
        try {
            await resetPasswordForEmail(data.email);
            setIsSent(true);
            toast({
                title: tc("success"),
                description: t("emailSentToast"),
            });
        } catch (error: any) {
            toast({
                title: tc("error"),
                description: error.message || t("errorToast"),
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    }

    async function handleDevReset() {
        const email = form.getValues().email;
        if (!email) {
            toast({
                title: tc("error"),
                description: t("emailRequiredToast"),
                variant: "destructive",
            });
            return;
        }

        const newPass = prompt("Enter new password for test account (min 6 chars):");
        if (!newPass || newPass.length < 6) return;

        setIsLoading(true);
        try {
            const res = await fetch("/api/auth/dev-reset", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, newPassword: newPass }),
            });
            const data = await res.json();

            if (res.ok) {
                toast({
                    title: t("devResetTitle"),
                    description: t("devResetDesc"),
                });
            } else {
                toast({
                    title: tc("error"),
                    description: data.error || t("devResetError"),
                    variant: "destructive",
                });
            }
        } catch (e) {
            toast({
                title: tc("error"),
                description: t("devResetConnectionError"),
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
                        {t("description")}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!isSent ? (
                        <Form {...form}>
                            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                <FormField
                                    control={form.control}
                                    name="email"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>{t("emailLabel")}</FormLabel>
                                            <FormControl>
                                                <Input placeholder={t("emailPlaceholder")} {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading ? t("sending") : t("submit")}
                                    {!isLoading && <Mail className="ml-2 h-4 w-4" />}
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center p-4 bg-green-50 text-green-800 rounded-lg dark:bg-green-900/20 dark:text-green-400">
                            <Mail className="mx-auto h-8 w-8 mb-2" />
                            <h3 className="font-semibold text-lg mb-1">{t("emailSentTitle")}</h3>
                            <p className="text-sm">
                                {t("emailSentDesc")}
                            </p>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex flex-col gap-4 border-t p-4">
                    <Link href="/login" className="flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        {t("backToLogin")}
                    </Link>

                    {isDevResetUiEnabled && (
                        <Button variant="outline" size="sm" type="button" onClick={handleDevReset} className="w-full text-xs text-orange-500 border-orange-200 hover:bg-orange-50">
                            <Bug className="h-3 w-3 mr-2" />
                            {t("devSection")}
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </main>
    );
}
