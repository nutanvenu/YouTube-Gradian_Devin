import { useState } from "react";
import { Text } from "react-native";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useNetworkStatus } from "@/state/network";
import { CardSurface, PrimaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

export default function ChildRequestsRoute() {
  const { isOffline } = useNetworkStatus();
  const [subject, setSubject] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: (requestType: "MORE_TIME" | "UNBLOCK_APP" | "UNBLOCK_SITE") => api.createRequest({ request_type: requestType, subject: subject || null, reason: reason || null }),
    onSuccess: (request) => setMessage(`Request ${request.state.toLowerCase()}. A parent can review it.`),
    onError: (error) => setMessage(error instanceof Error ? error.message : "Request could not be sent."),
  });
  return (
    <ScreenScaffold title="Ask for help">
      <SectionSurface>
        <Text>Requests need a network connection. If you are offline, ask a parent in person; Guardian does not pretend an offline request was delivered.</Text>
        {isOffline ? <Text>Offline · request sending is unavailable.</Text> : null}
        <TextField label="App or website (optional)" value={subject} onChangeText={setSubject} />
        <TextField label="Note to parent (optional)" value={reason} onChangeText={setReason} />
        {message ? <Text accessibilityLiveRegion="polite">{message}</Text> : null}
        <CardSurface>
          <PrimaryButton label="Ask for more time" disabled={isOffline || create.isPending} onPress={() => create.mutate("MORE_TIME")} />
          <PrimaryButton label="Ask to unblock app" disabled={isOffline || create.isPending || !subject} onPress={() => create.mutate("UNBLOCK_APP")} />
          <PrimaryButton label="Ask to unblock site" disabled={isOffline || create.isPending || !subject} onPress={() => create.mutate("UNBLOCK_SITE")} />
        </CardSurface>
      </SectionSurface>
    </ScreenScaffold>
  );
}
