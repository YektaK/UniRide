/**
 * Fail-closed travel-time matrix errors from the optimizer (audit C2).
 *
 * Operational travel times come only from the stored Supabase `time_matrix`.
 * When the optimizer cannot answer from it, unbound /optimize and /compare
 * return a redacted 503 or 422 with a fixed `detail`. The BFF turns those into
 * a clear, redacted error for the browser instead of a generic failure or an
 * empty/zero route. Nothing here echoes location codes, keys or provider errors.
 */

export const MATRIX_UNAVAILABLE_CODE = "travel_time_matrix_unavailable" as const;
export const MATRIX_LOCATIONS_MISSING_CODE = "travel_time_matrix_locations_missing" as const;

export type OptimizerMatrixErrorCode =
    | typeof MATRIX_UNAVAILABLE_CODE
    | typeof MATRIX_LOCATIONS_MISSING_CODE;

/** Fixed `detail` strings returned by the optimizer (see routers/optimization.py). */
export const OPTIMIZER_MATRIX_UNAVAILABLE_DETAIL = "travel-time matrix unavailable";
export const OPTIMIZER_MATRIX_LOCATIONS_DETAIL =
    "requested locations are missing from the travel-time matrix";

/** HTTP status the BFF returns to the browser for each code. */
export const MATRIX_ERROR_HTTP_STATUS: Record<OptimizerMatrixErrorCode, 503 | 422> = {
    [MATRIX_UNAVAILABLE_CODE]: 503,
    [MATRIX_LOCATIONS_MISSING_CODE]: 422,
};

/** Redacted, user-facing BFF messages (the app's API routes use Turkish). */
export const MATRIX_ERROR_MESSAGES: Record<OptimizerMatrixErrorCode, string> = {
    [MATRIX_UNAVAILABLE_CODE]:
        "Seyahat süresi matrisi şu anda kullanılamıyor; rota hesaplanamadı. Lütfen daha sonra tekrar deneyin veya yöneticiye başvurun.",
    [MATRIX_LOCATIONS_MISSING_CODE]:
        "Bazı duraklar kayıtlı seyahat süresi matrisinde bulunmuyor; rota hesaplanamadı.",
};

/**
 * Classify an optimizer error response. Only the exact fixed details count:
 * other 422s (schema or compute-policy validation) must keep their own path.
 */
export function classifyOptimizerMatrixError(
    status: number,
    detail: unknown
): OptimizerMatrixErrorCode | undefined {
    if (status === 503 && detail === OPTIMIZER_MATRIX_UNAVAILABLE_DETAIL) {
        return MATRIX_UNAVAILABLE_CODE;
    }
    if (status === 422 && detail === OPTIMIZER_MATRIX_LOCATIONS_DETAIL) {
        return MATRIX_LOCATIONS_MISSING_CODE;
    }
    return undefined;
}

/** Read the optimizer's `detail` from a failed response without throwing. */
export async function readOptimizerErrorDetail(response: Response): Promise<unknown> {
    try {
        const body: unknown = await response.json();
        if (body && typeof body === "object" && "detail" in body) {
            return (body as { detail: unknown }).detail;
        }
    } catch {
        // Non-JSON error body: nothing to classify.
    }
    return undefined;
}
