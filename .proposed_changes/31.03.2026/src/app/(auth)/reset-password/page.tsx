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

const resetPasswordSchema = z.object({
    password: z.string().min(6, { message: "Şifreniz en az 6 karakter olmalıdır." }),
    confirmPassword: z.string().min(6, { message: "Lütfen şifrenizi tekrar girin." }),
}).refine((data) => data.password === data.confirmPassword, {
    message: "Şifreler eşleşmiyor.",
    path: ["confirmPassword"],
});

type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
    const { toast } = useToast();
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [hasSessionError, setHasSessionError] = useState(false);

    useEffect(() => {
        // Check if the user arrived here with a valid recovery token URL
        const checkSession = async () => {
            try {
                const supabase = getSupabaseClient();
                const { data, error } = await supabase.auth.getSession();

                // When clicking a reset link, Supabase magically creates a session via the hash token
                if (error || !data.session) {
                    // It's possible the URL logic hasn't parsed the hash yet in some manual flows, 
                    // but for simplicity we rely on Supabase's automatic hash parsing in auth.getSession().
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
                title: "Şifre Güncellendi",
                description: "Şifreniz başarıyla değiştirildi. Şimdi giriş yapabilirsiniz.",
            });
            setTimeout(() => {
                router.push("/login");
            }, 3000);
        } catch (error: any) {
            toast({
                title: "Güncelleme Başarısız",
                description: error.message || "Şifre güncellenirken bir hata oluştu. Linkin süresi dolmuş olabilir.",
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
                    <CardTitle className="text-2xl font-bold text-primary">Yeni Şifre Belirle</CardTitle>
                    <CardDescription>
                        Lütfen hesabınız için yeni bir şifre girin.
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
                                            <FormLabel>Yeni Şifre</FormLabel>
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
                                            <FormLabel>Yeni Şifre (Tekrar)</FormLabel>
                                            <FormControl>
                                                <Input type="password" placeholder="••••••••" {...field} />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />

                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading ? "Güncelleniyor..." : "Şifremi Güncelle"}
                                    {!isLoading && <Lock className="ml-2 h-4 w-4" />}
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center p-4 bg-green-50 text-green-800 rounded-lg dark:bg-green-900/20 dark:text-green-400">
                            <CheckCircle className="mx-auto h-8 w-8 mb-2" />
                            <h3 className="font-semibold text-lg mb-1">Başarılı!</h3>
                            <p className="text-sm">
                                Şifreniz güncellendi. Giriş sayfasına yönlendiriliyorsunuz...
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </main>
    );
}
