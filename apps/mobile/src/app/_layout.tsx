import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { SessionProvider } from "@/auth/session";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } });

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <SessionProvider>
          <Stack screenOptions={{ headerShown: false }} />
        </SessionProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
