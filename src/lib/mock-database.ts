
import type { WeeklySchedule, ScheduleEntry, User, UserRole, RideRequest, RideStatus } from "@/types";

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
      ...existingUser, 
      ...updatedUserData,
      password: updatedUserData.password || existingUser.password,
      role: existingUser.role, // Ensure role is not changed via this function if not intended
    };
    
    // If role is student (should always be if using user-form-dialog as it preserves role)
    // and weeklyScheduleId is missing (e.g. admin was changed to student, which we disallowed, but for safety)
    if (mockUsers[userIndex].role === 'student' && !mockUsers[userIndex].weeklyScheduleId) {
        const newScheduleId = `schedule_usr_upd_${Date.now()}${Math.random().toString(36).substring(2,7)}`;
        mockUsers[userIndex].weeklyScheduleId = newScheduleId;
        createNewUserSchedule(mockUsers[userIndex].id, newScheduleId); // Ensure schedule exists
    }
    return true;
  }
  return false;
}

export function addUser(newUserData: Omit<User, 'id' | 'role' | 'weeklyScheduleId'> & {password?: string}): User | null {
    const newId = `user${Date.now()}${Math.random().toString(36).substring(2, 7)}`;
    const newScheduleId = `schedule_new_usr_${Date.now()}${Math.random().toString(36).substring(2,7)}`;

    const newUser: User = {
      ...newUserData,
      id: newId,
      role: "student", 
      password: newUserData.password || `pass${Math.random().toString(36).substring(2, 8)}`,
      weeklyScheduleId: newScheduleId,
      homeAddress: newUserData.homeAddress || "",
      accessibilityNeeds: newUserData.accessibilityNeeds || [],
    };

    mockUsers.push(JSON.parse(JSON.stringify(newUser)));
    createNewUserSchedule(newId, newScheduleId); 
    return JSON.parse(JSON.stringify(newUser));
}

export function deleteUser(userId: string): boolean {
  const userIndex = mockUsers.findIndex(u => u.id === userId);
  if (userIndex === -1) return false;

  const userScheduleId = mockUsers[userIndex].weeklyScheduleId;
  mockUsers.splice(userIndex, 1);

  if (userScheduleId && mockSchedules[userScheduleId]) {
    delete mockSchedules[userScheduleId];
  }
  return true;
}


// --- Schedule Data ---
const generateRandomTime = (minHour = 8, maxHour = 16): string => {
  const hour = Math.floor(Math.random() * (maxHour - minHour + 1)) + minHour;
  return `${hour.toString().padStart(2, '0')}:00`;
};

const generateRandomCourseCode = (): string => {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const numLetters = Math.random() < 0.5 ? 2 : 3;
  let code = "";
  for (let i = 0; i < numLetters; i++) {
    code += letters.charAt(Math.floor(Math.random() * letters.length));
  }
  for (let i = 0; i < 3; i++) {
    code += Math.floor(Math.random() * 10);
  }
  return code;
};

const generateRandomScheduleEntries = (): ScheduleEntry[] => {
    const entries: ScheduleEntry[] = [];
    const daysToHaveClasses = new Set<ScheduleEntry["dayOfWeek"]>();
    const availableDays: ScheduleEntry["dayOfWeek"][] = ["monday", "tuesday", "wednesday", "thursday", "friday"];
    
    while(daysToHaveClasses.size < 4 && availableDays.length > 0) {
        const randomIndex = Math.floor(Math.random() * availableDays.length);
        daysToHaveClasses.add(availableDays.splice(randomIndex, 1)[0]);
    }

    Array.from(daysToHaveClasses).forEach(day => {
        const numClassesToday = Math.floor(Math.random() * 3) + 1; // 1 to 3 classes
        let lastEndTime = "00:00";

        for (let i = 0; i < numClassesToday; i++) {
            let startTime = generateRandomTime();
            // Ensure startTime is after lastEndTime if it's not the first class of the day
            if (i > 0) {
                let attempts = 0;
                while (startTime <= lastEndTime && attempts < 10) { // Prevent infinite loops
                    startTime = generateRandomTime();
                    attempts++;
                }
                if (startTime <= lastEndTime) continue; // Skip if can't find a suitable slot
            }

            const durationHours = Math.floor(Math.random() * 3) + 2; // 2 to 4 hours
            const startHour = parseInt(startTime.split(":")[0]);
            let endHour = startHour + durationHours;
            
            if (endHour > 22) endHour = 22; // Cap end time to avoid going too late

            const endTime = `${endHour.toString().padStart(2, '0')}:00`;

            // Basic check to ensure endTime is after startTime and reasonable duration
            if (endTime <= startTime) continue; 

            entries.push({
                id: `se${day}${i}${Date.now()}${Math.random().toString(36).substring(2, 5)}`,
                dayOfWeek: day,
                courseName: generateRandomCourseCode(),
                startTime,
                endTime,
                location: Math.random() < 0.5 ? "Dudullu" : "Çengelköy",
            });
            lastEndTime = endTime; // Update last end time for the current day
        }
    });
    return entries.sort((a,b) => allPossibleDays.indexOf(a.dayOfWeek) - allPossibleDays.indexOf(b.dayOfWeek) || a.startTime.localeCompare(b.startTime));
};

let mockSchedules: Record<string, WeeklySchedule> = {
  "schedule001": {
    id: "schedule001", userId: "student001", lastUpdated: new Date().toISOString(),
    entries: generateRandomScheduleEntries()
  },
  "schedule002": {
    id: "schedule002", userId: "student002", lastUpdated: new Date().toISOString(),
    entries: generateRandomScheduleEntries()
  },
  "schedule003": {
    id: "schedule003", userId: "student003", lastUpdated: new Date().toISOString(),
    entries: generateRandomScheduleEntries()
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
        entries: [], // Initially empty, can be populated by admin or student
        lastUpdated: new Date().toISOString(),
    };
    mockSchedules[scheduleId] = JSON.parse(JSON.stringify(newSchedule));
    return JSON.parse(JSON.stringify(newSchedule));
}

// --- Ride Request Data ---
const createMockIsoDateTime = (dayOffset: number, hour: number, minute: number): string => {
  const date = new Date();
  date.setDate(date.getDate() + dayOffset);
  date.setHours(hour, minute, 0, 0);
  return date.toISOString();
};

let mockRideRequests: RideRequest[] = [
  {
    id: "req001",
    userId: "student001",
    type: "adhoc",
    requestedPickupTime: createMockIsoDateTime(-2, 9, 0),
    requestedDropoffTime: createMockIsoDateTime(-2, 17, 0),
    pickupLocation: { address: "123 Lale Sokak, Çankaya, Ankara" },
    dropoffLocation: { address: "ODTÜ Kampüsü, Ana Giriş" },
    status: "completed",
    createdAt: new Date(new Date().setDate(new Date().getDate() - 2)).toISOString(),
  },
  {
    id: "req002",
    userId: "student001",
    type: "scheduled",
    requestedPickupTime: createMockIsoDateTime(1, 8, 30),
    requestedDropoffTime: createMockIsoDateTime(1, 16, 30),
    pickupLocation: { address: "123 Lale Sokak, Çankaya, Ankara" },
    dropoffLocation: { address: "Mühendislik Fakültesi" },
    status: "confirmed",
    createdAt: new Date().toISOString(),
  },
  {
    id: "req003",
    userId: "student001",
    type: "adhoc",
    requestedPickupTime: createMockIsoDateTime(3, 10, 0),
    requestedDropoffTime: createMockIsoDateTime(3, 14, 0),
    pickupLocation: { address: "Ev Adresim (Değiştirilmiş)" },
    dropoffLocation: { address: "Kütüphane" },
    status: "pending_admin_approval",
    createdAt: new Date().toISOString(),
  },
    {
    id: "req004",
    userId: "student001",
    type: "scheduled",
    requestedPickupTime: createMockIsoDateTime(-1, 9, 15),
    requestedDropoffTime: createMockIsoDateTime(-1, 17, 45),
    pickupLocation: { address: "123 Lale Sokak, Çankaya, Ankara" },
    dropoffLocation: { address: "Yemekhane" },
    status: "cancelled_by_student",
    createdAt: new Date(new Date().setDate(new Date().getDate() -1)).toISOString(),
  },
  {
    id: "req005",
    userId: "student002", 
    type: "adhoc",
    requestedPickupTime: createMockIsoDateTime(0, 11, 0), 
    requestedDropoffTime: createMockIsoDateTime(0, 15, 30),
    pickupLocation: { address: "456 Menekşe Caddesi" },
    dropoffLocation: { address: "Spor Salonu" },
    status: "pending_admin_approval",
    createdAt: new Date().toISOString(),
  },
  {
    id: "req006",
    userId: "student003",
    type: "adhoc",
    requestedPickupTime: createMockIsoDateTime(2, 14, 0),
    requestedDropoffTime: createMockIsoDateTime(2, 18, 0),
    pickupLocation: { address: "789 Gül Apartmanı" },
    dropoffLocation: { address: "Sosyal Bilimler Binası" },
    status: "pending_admin_approval",
    createdAt: new Date().toISOString(),
  }
];

export function getRideRequests(): RideRequest[] {
  return JSON.parse(JSON.stringify(mockRideRequests));
}

export function updateRideRequestStatus(requestId: string, newStatus: RideStatus): boolean {
  const requestIndex = mockRideRequests.findIndex(req => req.id === requestId);
  if (requestIndex !== -1) {
    mockRideRequests[requestIndex].status = newStatus;
    return true;
  }
  return false;
}

export function addRideRequest(request: Omit<RideRequest, 'id' | 'createdAt'>): RideRequest {
    const newRequest: RideRequest = {
        ...request,
        id: `req${Date.now()}${Math.random().toString(36).substring(2,7)}`,
        createdAt: new Date().toISOString(),
    };
    mockRideRequests.push(JSON.parse(JSON.stringify(newRequest)));
    return JSON.parse(JSON.stringify(newRequest));
}

    