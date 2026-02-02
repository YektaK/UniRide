/**
 * Location Mapper
 * Maps student addresses to DouBus location codes
 * This is a simplified mapping - in production, you'd use geocoding/address matching
 */

import type { LocationCode } from "./route";

/**
 * Map address to DouBus location code
 * This is a simplified version - in production, use geocoding API
 */
export const addressToLocationCode = (address: string): LocationCode | null => {
  const normalized = address.toLowerCase().trim();
  
  // Simple keyword matching - can be enhanced with geocoding
  if (normalized.includes("sw1") || normalized.includes("sarıyer 1")) return "Sw1";
  if (normalized.includes("sw2") || normalized.includes("sarıyer 2")) return "Sw2";
  if (normalized.includes("sw3") || normalized.includes("sarıyer 3")) return "Sw3";
  if (normalized.includes("sw4") || normalized.includes("sarıyer 4")) return "Sw4";
  if (normalized.includes("sw5") || normalized.includes("sarıyer 5")) return "Sw5";
  if (normalized.includes("sw6") || normalized.includes("sarıyer 6")) return "Sw6";
  if (normalized.includes("sw7") || normalized.includes("sarıyer 7")) return "Sw7";
  if (normalized.includes("sw8") || normalized.includes("sarıyer 8")) return "Sw8";
  if (normalized.includes("sw9") || normalized.includes("sarıyer 9")) return "Sw9";
  
  if (normalized.includes("so1") || normalized.includes("sultangazi 1")) return "So1";
  if (normalized.includes("so2") || normalized.includes("sultangazi 2")) return "So2";
  if (normalized.includes("so3") || normalized.includes("sultangazi 3")) return "So3";
  if (normalized.includes("so4") || normalized.includes("sultangazi 4")) return "So4";
  if (normalized.includes("so5") || normalized.includes("sultangazi 5")) return "So5";
  if (normalized.includes("so6") || normalized.includes("sultangazi 6")) return "So6";
  if (normalized.includes("so7") || normalized.includes("sultangazi 7")) return "So7";
  if (normalized.includes("so8") || normalized.includes("sultangazi 8")) return "So8";
  if (normalized.includes("so9") || normalized.includes("sultangazi 9")) return "So9";
  if (normalized.includes("so10") || normalized.includes("sultangazi 10")) return "So10";
  if (normalized.includes("so11") || normalized.includes("sultangazi 11")) return "So11";
  if (normalized.includes("so12") || normalized.includes("sultangazi 12")) return "So12";
  if (normalized.includes("so13") || normalized.includes("sultangazi 13")) return "So13";
  if (normalized.includes("so14") || normalized.includes("sultangazi 14")) return "So14";
  if (normalized.includes("so15") || normalized.includes("sultangazi 15")) return "So15";
  if (normalized.includes("so16") || normalized.includes("sultangazi 16")) return "So16";
  if (normalized.includes("so17") || normalized.includes("sultangazi 17")) return "So17";
  if (normalized.includes("so18") || normalized.includes("sultangazi 18")) return "So18";
  if (normalized.includes("so19") || normalized.includes("sultangazi 19")) return "So19";
  
  // Default to closest location if no match
  // In production, use geocoding to find nearest location
  return "Sw1"; // Default fallback
};

/**
 * Get location code from coordinates (future enhancement)
 */
export const coordinatesToLocationCode = (
  lat: number,
  lng: number
): LocationCode | null => {
  // TODO: Implement geocoding-based location detection
  // For now, return null to use address-based mapping
  return null;
};

