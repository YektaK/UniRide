/**
 * Location Mapper - FIXED VERSION
 * Maps student addresses to DouBus location codes
 * 
 * FIXES:
 * 1. Removed dangerous default fallback to "Sw1"
 * 2. Returns null when no match found (safer behavior)
 * 3. Added better logging for debugging
 */

import type { LocationCode } from "./route";

// Location code mappings - keyword to location code
const LOCATION_MAPPINGS: Record<string, LocationCode> = {
  // Sarıyer (Sw) locations
  "sw1": "Sw1", "sarıyer 1": "Sw1",
  "sw2": "Sw2", "sarıyer 2": "Sw2",
  "sw3": "Sw3", "sarıyer 3": "Sw3",
  "sw4": "Sw4", "sarıyer 4": "Sw4",
  "sw5": "Sw5", "sarıyer 5": "Sw5",
  "sw6": "Sw6", "sarıyer 6": "Sw6",
  "sw7": "Sw7", "sarıyer 7": "Sw7",
  "sw8": "Sw8", "sarıyer 8": "Sw8",
  "sw9": "Sw9", "sarıyer 9": "Sw9",
  
  // Sultangazi (So) locations
  "so1": "So1", "sultangazi 1": "So1",
  "so2": "So2", "sultangazi 2": "So2",
  "so3": "So3", "sultangazi 3": "So3",
  "so4": "So4", "sultangazi 4": "So4",
  "so5": "So5", "sultangazi 5": "So5",
  "so6": "So6", "sultangazi 6": "So6",
  "so7": "So7", "sultangazi 7": "So7",
  "so8": "So8", "sultangazi 8": "So8",
  "so9": "So9", "sultangazi 9": "So9",
  "so10": "So10", "sultangazi 10": "So10",
  "so11": "So11", "sultangazi 11": "So11",
  "so12": "So12", "sultangazi 12": "So12",
  "so13": "So13", "sultangazi 13": "So13",
  "so14": "So14", "sultangazi 14": "So14",
  "so15": "So15", "sultangazi 15": "So15",
  "so16": "So16", "sultangazi 16": "So16",
  "so17": "So17", "sultangazi 17": "So17",
  "so18": "So18", "sultangazi 18": "So18",
  "so19": "So19", "sultangazi 19": "So19",
};

/**
 * Map address to DouBus location code
 * 
 * @param address - The address string to map
 * @returns LocationCode if found, null otherwise (FIXED: no default fallback)
 * 
 * @example
 * addressToLocationCode("Sw1 Mahallesi") // Returns "Sw1"
 * addressToLocationCode("Unknown Address") // Returns null (NOT "Sw1")
 */
export const addressToLocationCode = (address: string): LocationCode | null => {
  if (!address || typeof address !== "string") {
    console.warn("[LocationMapper] Invalid address provided:", address);
    return null;
  }

  const normalized = address.toLowerCase().trim();
  
  // Check each mapping
  for (const [keyword, locationCode] of Object.entries(LOCATION_MAPPINGS)) {
    if (normalized.includes(keyword)) {
      return locationCode;
    }
  }
  
  // No match found - return null instead of default
  console.warn(
    `[LocationMapper] No location code found for address: "${address}". ` +
    `Please update the student's address or add a new mapping.`
  );
  return null;
};

/**
 * Get location code from coordinates (future enhancement)
 * 
 * @param lat - Latitude
 * @param lng - Longitude
 * @returns LocationCode if found, null otherwise
 */
export const coordinatesToLocationCode = (
  lat: number,
  lng: number
): LocationCode | null => {
  // TODO: Implement geocoding-based location detection
  // Could use a spatial index or distance calculation to nearest known location
  console.warn(
    `[LocationMapper] coordinatesToLocationCode not implemented. ` +
    `Coordinates: (${lat}, ${lng})`
  );
  return null;
};

/**
 * Validate if a location code is valid
 */
export const isValidLocationCode = (code: string): code is LocationCode => {
  const validCodes = [
    "D.Kampus",
    "Sw1", "Sw2", "Sw3", "Sw4", "Sw5", "Sw6", "Sw7", "Sw8", "Sw9",
    "So1", "So2", "So3", "So4", "So5", "So6", "So7", "So8", "So9",
    "So10", "So11", "So12", "So13", "So14", "So15", "So16", "So17", "So18", "So19"
  ];
  return validCodes.includes(code);
};

/**
 * Get all valid location codes
 */
export const getAllLocationCodes = (): LocationCode[] => {
  return [
    "D.Kampus",
    "Sw1", "Sw2", "Sw3", "Sw4", "Sw5", "Sw6", "Sw7", "Sw8", "Sw9",
    "So1", "So2", "So3", "So4", "So5", "So6", "So7", "So8", "So9",
    "So10", "So11", "So12", "So13", "So14", "So15", "So16", "So17", "So18", "So19"
  ];
};
