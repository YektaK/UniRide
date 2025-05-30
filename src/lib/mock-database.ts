
import type { WeeklySchedule, ScheduleEntry, User, UserRole } from "@/types";

const allPossibleDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

// --- User Data ---
let mockUsers: User[] = [
  {
    id: "admin001",
    name: "Admin Kullanıcısı",
    email: "admin@uniride.com",
    password: "admin",
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
  // Return a deep copy to prevent direct mutation of the mockUsers array from outside
  return JSON.parse(JSON.stringify(mockUsers));
}

export function getUserById(id: string): User | undefined {
  const user = mockUsers.find(u => u.id === id);
  return user ? JSON.parse(JSON.stringify(user)) : undefined;
}

export function getUserByEmailOrStudentNumber(identifier: string, passwordInput: string): User | null {
  const lowerIdentifier = identifier.toLowerCase();
  const foundUser = mockUsers.find(
    u => (u.email.toLowerCase() === lowerIdentifier || u.studentNumber === lowerIdentifier) && u.password === passwordInput
  );
  return foundUser ? JSON.parse(JSON.stringify(foundUser)) : null;
}

export function updateUser(updatedUserData: User): boolean {
  const userIndex = mockUsers.findIndex(u => u.id === updatedUserData.id);
  if (userIndex !== -1) {
    mockUsers[userIndex] = JSON.parse(JSON.stringify(updatedUserData)); // Store a copy
    return true;
  }
  return false;
}

export function addUser(newUserData: Omit<User, 'id' | 'weeklyScheduleId' | 'role'> & {role?: UserRole}): User | null {
    const newId = `user${Date.now()}${Math.random().toString(36).substring(2, 7)}`;
    const newScheduleId = `schedule${Date.now()}${Math.random().toString(36).substring(2, 7)}`;
    
    const newUser: User = {
        ...newUserData,
        id: newId,
        role: "student", // New registrations are always students
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
  if (mockSchedules[userId]) { // Assuming scheduleId might be same as userId for simplicity here or derived
      // This needs to be more robust if scheduleId is different.
      // For now, let's assume we need to find scheduleId from user object.
      const userToDelete = mockUsers.find(u => u.id === userId); // User already deleted, so find from original if needed
      // This logic needs to be re-evaluated. For now, we don't delete schedule if user is deleted as scheduleId is separate.
  }
  return mockUsers.length < initialLength;
}


// --- Schedule Data ---
// Helper to generate a random time string (HH:MM) on the hour
function generateRandomTime(minHour = 8, maxHour = 16): string {
  const hour = Math.floor(Math.random() * (maxHour - minHour + 1)) + minHour;
  return `${String(hour).padStart(2, '0')}:00`;
}

// Helper to generate a random course code (e.g., CS101, MAT202)
function generateRandomCourseCode(): string {
  const prefixes = ["CS", "MAT", "PHY", "ENG", "ECO", "HIS", "ART", "BIO", "CHE", "GEO", "LAW", "PSY", "SOC", "BUS", "PHI"];
  const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];
  const number = Math.floor(Math.random() * 300) + 101; // e.g., 101-401
  return `${prefix}${number}`;
}

// Helper to generate random schedule entries for a student
function generateRandomScheduleEntries(): ScheduleEntry[] {
  const entries: ScheduleEntry[] = [];
  const days: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday"];
  const selectedDays = new Set<ScheduleEntry["dayOfWeek"]>();

  // Ensure 4 distinct days are selected
  while (selectedDays.size < 4) {
    selectedDays.add(days[Math.floor(Math.random() * days.length)]);
  }

  Array.from(selectedDays).forEach(day => {
    const numClassesToday = Math.floor(Math.random() * 3) + 1; // 1 to 3 classes
    let lastEndTime = "00:00";

    for (let i = 0; i < numClassesToday; i++) {
      let startTime: string;
      let endTime: string;
      let attempts = 0;
      const maxAttempts = 10; // Prevent infinite loop

      // Find a non-overlapping time slot
      do {
        startTime = generateRandomTime(8, 15); // Classes can start between 8 AM and 3 PM
        const duration = (Math.floor(Math.random() * 3) + 2) * 60; // 2, 3, or 4 hours in minutes
        const startMinutes = parseInt(startTime.split(':')[0], 10) * 60;
        const endTotalMinutes = startMinutes + duration;
        const endHour = Math.floor(endTotalMinutes / 60);
        const endMinute = endTotalMinutes % 60; // Should always be 00 with current logic
        endTime = `${String(endHour).padStart(2, '0')}:${String(endMinute).padStart(2, '0')}`;
        attempts++;
      } while (startTime < lastEndTime && attempts < maxAttempts && parseInt(endTime.split(':')[0],10) <= 19); // Ensure class ends by 7 PM

      if (attempts >= maxAttempts || parseInt(endTime.split(':')[0],10) > 19 ) continue; // Skip if no suitable slot found or ends too late


      lastEndTime = endTime;

      entries.push({
        id: `se${day}${i}${Date.now()}${Math.random().toString(36).substring(2, 5)}`,
        dayOfWeek: day,
        courseName: generateRandomCourseCode(),
        startTime,
        endTime,
        location: Math.random() < 0.5 ? "Dudullu" : "Çengelköy",
      });
    }
  });
  // Sort entries for consistency
  return entries.sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));
}


let mockSchedules: Record<string, WeeklySchedule> = {
  "schedule001": { // Ayşe
    id: "schedule001",
    userId: "student001",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
  },
  "schedule002": { // Veli
    id: "schedule002",
    userId: "student002",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
  },
  "schedule003": { // Zeynep
    id: "schedule003",
    userId: "student003",
    entries: generateRandomScheduleEntries(),
    lastUpdated: new Date().toISOString(),
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
        // This case should ideally not happen if scheduleId is truly unique
        return JSON.parse(JSON.stringify(mockSchedules[scheduleId]));
    }
    const newSchedule: WeeklySchedule = {
        id: scheduleId,
        userId: userId,
        entries: [], // Start with an empty schedule
        lastUpdated: new Date().toISOString(),
    };
    mockSchedules[scheduleId] = JSON.parse(JSON.stringify(newSchedule));
    return JSON.parse(JSON.stringify(newSchedule));
}
