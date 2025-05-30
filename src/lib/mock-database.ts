
import type { WeeklySchedule, ScheduleEntry, User, UserRole } from "@/types";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

// --- User Data ---
let mockUsers: User[] = [
  {
    id: "admin001",
    name: "Admin Kullanıcısı",
    email: "admin@uniride.com",
    password: "admin", // Default admin password
    role: "admin",
    homeAddress: "Üniversite Yönetim Binası",
  },
  {
    id: "student001",
    name: "Öğrenci Ayşe",
    email: "student@uniride.com",
    password: "studentpassword",
    role: "student",
    studentNumber: "202003002001",
    homeAddress: "123 Lale Sokak, Çankaya, Ankara",
    accessibilityNeeds: ["wheelchair"],
    weeklyScheduleId: "schedule001",
  },
  {
    id: "student002",
    name: "Öğrenci Veli",
    email: "veli@uniride.com",
    password: "velipassword",
    role: "student",
    studentNumber: "202003002002",
    homeAddress: "456 Menekşe Caddesi, Yenimahalle, Ankara",
    accessibilityNeeds: [],
    weeklyScheduleId: "schedule002",
  },
  {
    id: "student003",
    name: "Öğrenci Zeynep",
    email: "zeynep@uniride.com",
    password: "zeyneppassword",
    role: "student",
    studentNumber: "202003002003",
    homeAddress: "789 Gül Apartmanı, Keçiören, Ankara",
    accessibilityNeeds: ["visual_impairment"],
    weeklyScheduleId: "schedule003",
  },
];

export function getUsers(): User[] {
  return JSON.parse(JSON.stringify(mockUsers));
}

export function getUserById(id: string): User | undefined {
  const user = mockUsers.find(u => u.id === id);
  return user ? JSON.parse(JSON.stringify(user)) : undefined;
}

export function getUserByEmailOrStudentNumber(identifier: string, passwordInput: string): User | null {
  const lowerIdentifier = identifier.toLowerCase();
  const foundUser = mockUsers.find(
    u => (u.email.toLowerCase() === lowerIdentifier || (u.studentNumber && u.studentNumber === identifier)) && u.password === passwordInput
  );
  return foundUser ? JSON.parse(JSON.stringify(foundUser)) : null;
}

export function updateUser(updatedUserData: User): boolean {
  const userIndex = mockUsers.findIndex(u => u.id === updatedUserData.id);
  if (userIndex !== -1) {
    const existingUser = mockUsers[userIndex];
    mockUsers[userIndex] = {
      ...existingUser, // Preserve fields like password, weeklyScheduleId unless explicitly changed
      ...updatedUserData,
      // Ensure password is not accidentally cleared if not part of updatedUserData
      password: updatedUserData.password || existingUser.password,
    };
    // If role changed to student and weeklyScheduleId is missing, create one
    if (mockUsers[userIndex].role === 'student' && !mockUsers[userIndex].weeklyScheduleId) {
        const newScheduleId = `schedule${Date.now()}${Math.random().toString(36).substring(2,7)}`;
        mockUsers[userIndex].weeklyScheduleId = newScheduleId;
        createNewUserSchedule(mockUsers[userIndex].id, newScheduleId);
    }
    return true;
  }
  return false;
}

export function addUser(newUserData: Omit<User, 'id' | 'role' | 'weeklyScheduleId'> & {role?: UserRole, password?: string}): User | null {
    const newId = `user${Date.now()}${Math.random().toString(36).substring(2, 7)}`;
    const newScheduleId = `schedule${Date.now()}${Math.random().toString(36).substring(2, 7)}`;

    const newUser: User = {
      ...newUserData,
      id: newId,
      role: "student", // New registrations via student form are always students
      password: newUserData.password || `pass${Math.random().toString(36).substring(2, 8)}`, // Assign a random password if not provided
      weeklyScheduleId: newScheduleId,
    };

    mockUsers.push(JSON.parse(JSON.stringify(newUser)));
    createNewUserSchedule(newId, newScheduleId); // Create an empty schedule for the new user
    return JSON.parse(JSON.stringify(newUser));
}

export function deleteUser(userId: string): boolean {
  const initialLength = mockUsers.length;
  mockUsers = mockUsers.filter(u => u.id !== userId);
  // Also delete their schedule if it exists
  const userScheduleId = mockSchedules[userId]?.id; // This logic might need refinement based on how schedule IDs are linked
  if (userScheduleId && mockSchedules[userScheduleId]) {
    delete mockSchedules[userScheduleId];
  }
  return mockUsers.length < initialLength;
}


// --- Schedule Data ---

let mockSchedules: Record<string, WeeklySchedule> = {
  "schedule001": {
    id: "schedule001", userId: "student001", lastUpdated: "2024-05-15T10:00:00.000Z",
    entries: [
      { id: "s1m1", dayOfWeek: "monday", courseName: "MAT101", startTime: "09:00", endTime: "11:00", location: "Dudullu" },
      { id: "s1m2", dayOfWeek: "monday", courseName: "PHY101", startTime: "13:00", endTime: "15:00", location: "Çengelköy" },
      { id: "s1t1", dayOfWeek: "tuesday", courseName: "ENG101", startTime: "10:00", endTime: "12:00", location: "Dudullu" },
      { id: "s1w1", dayOfWeek: "wednesday", courseName: "CS101", startTime: "11:00", endTime: "14:00", location: "Çengelköy" },
      { id: "s1f1", dayOfWeek: "friday", courseName: "HIS101", startTime: "14:00", endTime: "17:00", location: "Dudullu" },
    ]
  },
  "schedule002": {
    id: "schedule002", userId: "student002", lastUpdated: "2024-05-15T10:00:00.000Z",
    entries: [
      { id: "s2m1", dayOfWeek: "monday", courseName: "ECO202", startTime: "10:00", endTime: "13:00", location: "Çengelköy" },
      { id: "s2w1", dayOfWeek: "wednesday", courseName: "STA201", startTime: "09:00", endTime: "11:00", location: "Dudullu" },
      { id: "s2w2", dayOfWeek: "wednesday", courseName: "ACC201", startTime: "14:00", endTime: "16:00", location: "Dudullu" },
      { id: "s2th1", dayOfWeek: "thursday", courseName: "FIN201", startTime: "11:00", endTime: "13:00", location: "Çengelköy" },
      { id: "s2f1", dayOfWeek: "friday", courseName: "MKT201", startTime: "13:00", endTime: "15:00", location: "Dudullu" },
    ]
  },
  "schedule003": {
    id: "schedule003", userId: "student003", lastUpdated: "2024-05-15T10:00:00.000Z",
    entries: [
      { id: "s3t1", dayOfWeek: "tuesday", courseName: "ART100", startTime: "09:00", endTime: "12:00", location: "Dudullu" },
      { id: "s3t2", dayOfWeek: "tuesday", courseName: "MUS100", startTime: "14:00", endTime: "16:00", location: "Çengelköy" },
      { id: "s3th1", dayOfWeek: "thursday", courseName: "DRA100", startTime: "10:00", endTime: "13:00", location: "Dudullu" },
      { id: "s3f1", dayOfWeek: "friday", courseName: "PHL100", startTime: "11:00", endTime: "14:00", location: "Çengelköy" },
    ]
  },
};

export function getStudentSchedule(scheduleId: string): WeeklySchedule | undefined {
  const schedule = mockSchedules[scheduleId];
  if (schedule) {
    return JSON.parse(JSON.stringify(schedule));
  }
  return undefined;
}

export function updateStudentScheduleEntries(scheduleId: string, entries: ScheduleEntry[]): boolean {
  if (mockSchedules[scheduleId]) {
    const sortedEntries = [...entries].sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));
    mockSchedules[scheduleId].entries = sortedEntries;
    mockSchedules[scheduleId].lastUpdated = new Date().toISOString();
    return true;
  }
  return false;
}

export function createNewUserSchedule(userId: string, scheduleId: string): WeeklySchedule {
    if (mockSchedules[scheduleId]) {
        return JSON.parse(JSON.stringify(mockSchedules[scheduleId]));
    }
    const newSchedule: WeeklySchedule = {
        id: scheduleId,
        userId: userId,
        entries: [],
        lastUpdated: new Date().toISOString(),
    };
    mockSchedules[scheduleId] = JSON.parse(JSON.stringify(newSchedule));
    return JSON.parse(JSON.stringify(newSchedule));
}

// Function to generate multiple random schedules for initial setup
export function generateInitialSchedules() {
    // This function can be called once if needed to populate mockSchedules
    // For Ayşe, Veli, Zeynep - their schedules are already defined above.
    // If more students were added programmatically and needed random schedules:
    // mockUsers.forEach(user => {
    //   if (user.role === 'student' && user.weeklyScheduleId && !mockSchedules[user.weeklyScheduleId]) {
    //      const entries = generateRandomScheduleEntries(); // Assume this function exists and is defined
    //      mockSchedules[user.weeklyScheduleId] = {
    //         id: user.weeklyScheduleId,
    //         userId: user.id,
    //         entries: entries,
    //         lastUpdated: new Date().toISOString(),
    //      };
    //   }
    // });
}
// Helper function for random entries (example, not used for the static data above)
// function generateRandomScheduleEntries(): ScheduleEntry[] { /* ... complex logic ... */ return []; }
// function generateRandomTime(minHour = 8, maxHour = 16): string { /* ... */ return "09:00"; }
// function generateRandomCourseCode(): string { /* ... */ return "CS101"; }
