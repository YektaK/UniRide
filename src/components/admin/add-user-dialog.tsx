
"use client";

import { useTranslations } from 'next-intl';
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
        disabilityType?: string | null;
    }) => void;
}

const addUserFormSchema = z.object({
    name: z.string().min(2, { message: "Full name must be at least 2 characters." }),
    email: z.string().email({ message: "Please enter a valid email address." }),
    password: z.string().min(6, { message: "Password must be at least 6 characters." }),
    role: z.enum(["student", "admin", "driver"]),
    studentNumber: z.string().optional(),
    disabilityType: z.enum(["Sw", "So"]).nullable().optional(),
}).refine(data => {
    if (data.role === "student" && (!data.studentNumber || !/^\d{12}$/.test(data.studentNumber))) {
        return false;
    }
    return true;
}, {
    message: "Student number is required for the Student role.",
    path: ["studentNumber"],
});

type AddUserFormValues = z.infer<typeof addUserFormSchema>;

export default function AddUserDialog({ isOpen, onClose, onSave }: AddUserDialogProps) {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const t = useTranslations('component.adminAddUserDialog');
    const tc = useTranslations('common');

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
            });
            onClose();
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>{t('title')}</DialogTitle>
                    <DialogDescription>
                        {t('description')}
                    </DialogDescription>
                </DialogHeader>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4">
                        <FormField
                            control={form.control}
                            name="name"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel>{t('nameLabel')}</FormLabel>
                                    <FormControl>
                                        <Input placeholder={t('namePlaceholder')} {...field} />
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
                                    <FormLabel>{t('emailLabel')}</FormLabel>
                                    <FormControl>
                                        <Input type="email" placeholder={t('emailPlaceholder')} {...field} />
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
                                    <FormLabel>{t('passwordLabel')}</FormLabel>
                                    <FormControl>
                                        <Input type="password" placeholder={t('passwordPlaceholder')} {...field} />
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
                                    <FormLabel>{t('roleLabel')}</FormLabel>
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <FormControl>
                                            <SelectTrigger>
                                                <SelectValue placeholder={t('rolePlaceholder')} />
                                            </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                            <SelectItem value="student">{t('roleStudent')}</SelectItem>
                                            <SelectItem value="driver">{t('roleDriver')}</SelectItem>
                                            <SelectItem value="admin">{t('roleAdmin')}</SelectItem>
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
                                        <FormLabel>{t('studentNumberLabel')}</FormLabel>
                                        <FormControl>
                                            <Input placeholder={t('studentNumberPlaceholder')} {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        )}
                        <DialogFooter className="pt-4">
                            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                                {tc('cancel')}
                            </Button>
                            <Button type="submit" disabled={isSubmitting}>
                                {isSubmitting ? t('adding') : t('submit')}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
