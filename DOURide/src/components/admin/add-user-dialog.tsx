
"use client";

import type { UserRole } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
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
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import React, { useEffect, useState } from "react";

interface AddUserDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (userData: {
        email: string;
        password: string;
        name: string;
        role: string;
        studentNumber?: string;
    }) => void;
}

const addUserFormSchema = z.object({
    name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
    email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
    password: z.string().min(6, { message: "Şifre en az 6 karakter olmalıdır." }),
    role: z.enum(["student", "admin", "driver"]),
    studentNumber: z.string().optional(),
    disabilityType: z.enum(["Sw", "So"]).nullable().optional(),
}).refine(data => {
    if (data.role === "student" && (!data.studentNumber || !/^\d{12}$/.test(data.studentNumber))) {
        return false;
    }
    return true;
}, {
    message: "Öğrenci rolü için 12 haneli öğrenci numarası gereklidir.",
    path: ["studentNumber"],
});

type AddUserFormValues = z.infer<typeof addUserFormSchema>;

export default function AddUserDialog({ isOpen, onClose, onSave }: AddUserDialogProps) {
    const [isSubmitting, setIsSubmitting] = useState(false);

    const form = useForm<AddUserFormValues>({
        resolver: zodResolver(addUserFormSchema),
        defaultValues: {
            name: "",
            email: "",
            password: "",
            role: "student",
            studentNumber: "",
            disabilityType: null,
        },
    });

    const watchedRole = form.watch("role");

    useEffect(() => {
        if (isOpen) {
            form.reset({
                name: "",
                email: "",
                password: "",
                role: "student",
                studentNumber: "",
                disabilityType: null,
            });
        }
    }, [isOpen, form]);

    const handleSubmit = async (data: AddUserFormValues) => {
        setIsSubmitting(true);
        try {
            await onSave({
                email: data.email,
                password: data.password,
                name: data.name,
                role: data.role,
                studentNumber: data.role === "student" ? data.studentNumber : undefined,
                // Ensure null for admin/driver
                disabilityType: data.role === "student" ? data.disabilityType : null,
            } as any);
            onClose();
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Yeni Kullanıcı Ekle</DialogTitle>
                    <DialogDescription>
                        Sisteme yeni bir kullanıcı ekleyin. Şifre güvenli bir şekilde oluşturulacaktır.
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Ad Soyad</FormLabel>
                                    <FormControl>
                                        <Input placeholder="Örn: Ahmet Yılmaz" {...field} />
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
                                    <FormLabel>E-posta</FormLabel>
                                    <FormControl>
                                        <Input type="email" placeholder="ornek@dogus.edu.tr" {...field} />
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
                                    <FormLabel>Şifre</FormLabel>
                                    <FormControl>
                                        <Input type="password" placeholder="En az 6 karakter" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="role"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>Rol</FormLabel>
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Rol seçin" />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="student">Öğrenci</SelectItem>
                                            <SelectItem value="driver">Şoför</SelectItem>
                                            <SelectItem value="admin">Admin</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        {watchedRole === "student" && (
                            <FormField
                                control={form.control}
                                name="studentNumber"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Öğrenci Numarası</FormLabel>
                                        <FormControl>
                                            <Input placeholder="12 haneli numara" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        )}
                        <DialogFooter className="pt-4">
                            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                                İptal
                            </Button>
                            <Button type="submit" disabled={isSubmitting}>
                                {isSubmitting ? "Ekleniyor..." : "Kullanıcı Ekle"}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
