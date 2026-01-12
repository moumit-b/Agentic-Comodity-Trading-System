'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

export function useApi<T>(
  fetchFn: () => Promise<T>,
  refreshInterval?: number,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const fetchFnRef = useRef(fetchFn);
  const isMountedRef = useRef(true);

  // Keep fetchFn ref up to date
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      const result = await fetchFnRef.current();
      if (isMountedRef.current) {
        setData(result);
        setError(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err as Error);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    // Initial fetch
    refetch();

    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Setup new interval if specified
    if (refreshInterval) {
      intervalRef.current = setInterval(() => {
        refetch();
      }, refreshInterval);
    }

    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [refetch, refreshInterval, ...dependencies]);

  return { data, loading, error, refetch };
}
