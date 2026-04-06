/**
 * Coordinate Utilities
 * DMS (Degrees Minutes Seconds) to Decimal conversion and related functions
 */

export interface Coordinates {
    lat: number;
    lng: number;
}

/**
 * Convert DMS (Degrees Minutes Seconds) string to decimal degrees
 * Example input: "41°00'04.9\"N" or "29°06'35.3\"E"
 * Example output: 41.0013611 or 29.1098055
 */
export function dmsToDecimal(dms: string): number {
    // Pattern: 41°00'04.9"N or 41°00'04.9"S
    const regex = /(\d+)°(\d+)'(\d+\.?\d*)"([NSEW])/i;
    const match = dms.match(regex);

    if (!match) {
        console.warn(`Invalid DMS format: ${dms}`);
        return 0;
    }

    const degrees = parseFloat(match[1]);
    const minutes = parseFloat(match[2]);
    const seconds = parseFloat(match[3]);
    const direction = match[4].toUpperCase();

    let decimal = degrees + (minutes / 60) + (seconds / 3600);

    // South and West are negative
    if (direction === 'S' || direction === 'W') {
        decimal = -decimal;
    }

    return decimal;
}

/**
 * Parse a coordinate pair from DMS strings
 * Example: "41°00'04.9\"N 29°06'35.3\"E"
 */
export function parseDmsCoordinates(coordString: string): Coordinates | null {
    // Split by space to get lat and lng parts
    const parts = coordString.trim().split(/\s+/);

    if (parts.length < 2) {
        console.warn(`Invalid coordinate pair: ${coordString}`);
        return null;
    }

    // Find lat (N/S) and lng (E/W)
    let lat = 0;
    let lng = 0;

    for (const part of parts) {
        if (part.includes('N') || part.includes('S')) {
            lat = dmsToDecimal(part);
        } else if (part.includes('E') || part.includes('W')) {
            lng = dmsToDecimal(part);
        }
    }

    return { lat, lng };
}

/**
 * Convert decimal degrees to DMS string
 * Example: 41.0013611, true -> "41°00'04.9\"N"
 */
export function decimalToDms(decimal: number, isLatitude: boolean): string {
    const absolute = Math.abs(decimal);
    const degrees = Math.floor(absolute);
    const minutesDecimal = (absolute - degrees) * 60;
    const minutes = Math.floor(minutesDecimal);
    const seconds = (minutesDecimal - minutes) * 60;

    let direction: string;
    if (isLatitude) {
        direction = decimal >= 0 ? 'N' : 'S';
    } else {
        direction = decimal >= 0 ? 'E' : 'W';
    }

    return `${degrees}°${minutes.toString().padStart(2, '0')}'${seconds.toFixed(1)}"${direction}`;
}

/**
 * Calculate distance between two coordinates using Haversine formula
 * Returns distance in kilometers
 */
export function haversineDistance(coord1: Coordinates, coord2: Coordinates): number {
    const R = 6371; // Earth's radius in km
    const dLat = toRad(coord2.lat - coord1.lat);
    const dLng = toRad(coord2.lng - coord1.lng);

    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(coord1.lat)) * Math.cos(toRad(coord2.lat)) *
        Math.sin(dLng / 2) * Math.sin(dLng / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function toRad(deg: number): number {
    return deg * (Math.PI / 180);
}

/**
 * Estimate travel time based on distance
 * Uses average speed assumption (default 30 km/h for city traffic)
 */
export function estimateTravelTime(distanceKm: number, avgSpeedKmh: number = 30): number {
    return (distanceKm / avgSpeedKmh) * 60; // Returns minutes
}
