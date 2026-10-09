/**
 * Supabase Authentication Helper Functions
 * Implements authentication using Supabase Auth
 */

import { getSupabaseClient } from "./supabase";
import { getUserByEmail, getUserByStudentNumber, createUser, updateUser, createSchedule } from "./database";
import type { DbUser } from "@/types/db";
import type { User } from "@/types";

/**
 * Convert DbUser to User (for backward compatibility)
 */
const dbUserToUser = (dbUser: DbUser): User => {
  return {
    id: dbUser.id,
    name: dbUser.name,
    email: dbUser.email,
    role: dbUser.role,
    studentNumber: dbUser.studentNumber,
    homeAddress: dbUser.homeAddress,
    homeCoordinates: dbUser.homeCoordinates,
    accessibilityNeeds: dbUser.accessibilityNeeds,
    weeklyScheduleId: dbUser.weeklyScheduleId,
  };
};

/**
 * Sign in with email and password
 */
export const signIn = async (
  emailOrStudentNumber: string,
  password: string
): Promise<User | null> => {
  try {
    let email = emailOrStudentNumber.toLowerCase();

    // Try email first
    const supabaseClient = getSupabaseClient();
    let { data: authData, error: authError } = await supabaseClient.auth.signInWithPassword({
      email,
      password,
    });

    // If email fails, try student number
    if (authError || !authData.user) {
      const user = await getUserByStudentNumber(emailOrStudentNumber);
      if (user && user.email) {
        email = user.email.toLowerCase();
        const result = await supabaseClient.auth.signInWithPassword({
          email,
          password,
        });
        authData = result.data;
        authError = result.error;
      }
    }

    if (authError || !authData.user) {
      console.error("Sign in error:", authError);
      return null;
    }

    // Get user data from database
    const dbUser = await getUserByEmail(authData.user.email!);
    if (!dbUser) {
      console.error("User not found in database");
      return null;
    }

    return dbUserToUser(dbUser);
  } catch (error) {
    console.error("Sign in error:", error);
    return null;
  }
};

/**
 * Reset Password (Send Email)
 */
export const resetPasswordForEmail = async (email: string): Promise<void> => {
  try {
    const supabaseClient = getSupabaseClient();
    const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    if (error) {
      console.error("Password reset error:", error);
      throw error;
    }
  } catch (error) {
    console.error("Password reset error:", error);
    throw error;
  }
};

/**
 * Update Password (from Reset Link)
 */
export const updatePassword = async (newPassword: string): Promise<void> => {
  try {
    const supabaseClient = getSupabaseClient();
    const { error } = await supabaseClient.auth.updateUser({
      password: newPassword
    });

    if (error) {
      console.error("Password update error:", error);
      throw error;
    }
  } catch (error) {
    console.error("Password update error:", error);
    throw error;
  }
};

/**
 * Register new user.
 * Self-registration is always role "student" (audit C1): admin/driver accounts
 * are created only through the service-role admin route.
 */
export const signUp = async (
  email: string,
  password: string,
  name: string,
  studentNumber?: string,
  userData?: Partial<Pick<DbUser, 'homeAddress' | 'accessibilityNeeds' | 'passwordHint'>>
): Promise<User | null> => {
  try {
    // Create user in Supabase Auth
    const supabaseClient = getSupabaseClient();
    const { data: authData, error: authError } = await supabaseClient.auth.signUp({
      email: email.toLowerCase(),
      password,
    });

    if (authError || !authData.user) {
      console.error("Sign up error:", authError);
      throw authError || new Error("Failed to create user");
    }

    // Create user document in database FIRST (before schedule due to foreign key)
    const newUser: DbUser = {
      id: authData.user.id,
      name,
      email: authData.user.email!,
      role: "student",
      studentNumber,
      passwordHint: userData?.passwordHint,
      homeAddress: userData?.homeAddress || "",
      accessibilityNeeds: userData?.accessibilityNeeds || [],
      weeklyScheduleId: undefined,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    await createUser(newUser, authData.user.id);

    // Self-registration always creates a student: create the weekly schedule AFTER the user exists
    const schedule = await createSchedule({
      userId: authData.user.id,
      entries: [],
      lastUpdated: new Date().toISOString()
    });
    const weeklyScheduleId = schedule.id;

    // Update user with schedule id
    await updateUser(authData.user.id, { weeklyScheduleId });
    newUser.weeklyScheduleId = weeklyScheduleId;

    return dbUserToUser(newUser);
  } catch (error) {
    console.error("Sign up error:", error);
    throw error;
  }
};

/**
 * Register new user (wrapper for signUp)
 * This function is for compatibility with register-form.tsx
 */
export const register = async (
  email: string,
  password: string,
  // role is deliberately not accepted: self-registration is always a student (audit C1)
  userData: Omit<DbUser, 'id' | 'email' | 'createdAt' | 'updatedAt' | 'weeklyScheduleId' | 'role'>
): Promise<User> => {
  const result = await signUp(
    email,
    password,
    userData.name,
    userData.studentNumber,
    {
      homeAddress: userData.homeAddress,
      accessibilityNeeds: userData.accessibilityNeeds,
      passwordHint: userData.passwordHint
    }
  );

  if (!result) {
    throw new Error("Failed to register user");
  }

  return result;
};

/**
 * Sign out user
 */
export const signOutUser = async (): Promise<void> => {
  try {
    const supabaseClient = getSupabaseClient();
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
      console.error("Sign out error:", error);
      throw error;
    }
  } catch (error) {
    console.error("Sign out error:", error);
    throw error;
  }
};

/**
 * Listen to auth state changes.
 *
 * The listener handed to supabase auth-js MUST stay synchronous. auth-js invokes it while it
 * holds its internal lock; awaiting a database query inside it (which itself calls
 * auth.getSession()) deadlocks that lock, so getSession() never resolves and every authenticated
 * request hangs until a reload (audit M13). The profile lookup is therefore deferred to a fresh
 * task outside the lock, and each event gets a sequence number so a late lookup can never
 * overwrite a newer event (e.g. resurrect a user after SIGNED_OUT) or run after unsubscribe.
 */
export const onAuthStateChange = (
  callback: (user: User | null) => void,
  onImmediateAuthEvent?: () => void,
): (() => void) => {
  const supabaseClient = getSupabaseClient();
  let latestEventId = 0;

  const loadProfile = async (email: string, eventId: number): Promise<void> => {
    let nextUser: User | null;
    try {
      const dbUser = await getUserByEmail(email);
      // A missing row can happen during registration (user exists in Auth but not yet in the database).
      nextUser = dbUser ? dbUserToUser(dbUser) : null;
    } catch (caught: unknown) {
      const error = caught as { code?: string } | null;
      // Only log actual errors, not expected cases like RLS blocking or user not found
      if (error?.code && error.code !== "PGRST116" && error.code !== "42501") {
        console.error("Error getting user:", error);
      }
      nextUser = null;
    }
    if (eventId !== latestEventId) return; // superseded by a newer event or unsubscribed
    callback(nextUser);
  };

  const { data: { subscription } } = supabaseClient.auth.onAuthStateChange((_event, session) => {
    const eventId = ++latestEventId;
    onImmediateAuthEvent?.();
    const email = session?.user?.email;
    if (!email) {
      callback(null);
      return;
    }
    setTimeout(() => {
      if (eventId !== latestEventId) return;
      void loadProfile(email, eventId);
    }, 0);
  });

  // Return unsubscribe function
  return () => {
    latestEventId++;
    subscription.unsubscribe();
  };
};

/**
 * Get current user
 */
export const getCurrentUser = async (): Promise<User | null> => {
  try {
    const supabaseClient = getSupabaseClient();
    const { data: { user: authUser }, error } = await supabaseClient.auth.getUser();

    if (error || !authUser) {
      return null;
    }

    const dbUser = await getUserByEmail(authUser.email!);
    if (!dbUser) {
      return null;
    }

    return dbUserToUser(dbUser);
  } catch (error) {
    console.error("Error getting current user:", error);
    return null;
  }
};
