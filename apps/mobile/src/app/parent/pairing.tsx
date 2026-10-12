import { useCallback, useEffect, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import QRCode from "react-native-qrcode-svg";
import { Text } from "react-native";
import { api, Pairing } from "@/api/client";
import { DataState, PrimaryButton, ScreenScaffold, SectionSurface } from "@/design-system";

export default function ParentPairingRoute() {
  const { familyId, childId } = useLocalSearchParams<{ familyId: string; childId: string }>();
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [remaining, setRemaining] = useState<string>("Unknown");
  const [failed, setFailed] = useState(false);
  const [expired, setExpired] = useState(false);
  const regenerate = useCallback(() => {
    setPairing(null); setFailed(false); setExpired(false);
    void api.createPairing(familyId, childId).then(setPairing).catch(() => setFailed(true));
  }, [childId, familyId]);
  useEffect(regenerate, [regenerate]);
  useEffect(() => {
    if (!pairing) return;
    const update = () => {
      const seconds = Math.max(0, Math.floor((new Date(pairing.expires_at).getTime() - Date.now()) / 1000));
      setRemaining(`${Math.floor(seconds / 60)}m ${seconds % 60}s`);
      setExpired(seconds === 0);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [pairing]);
  return <ScreenScaffold title="Pair a child device"><DataState state={failed ? "error" : pairing ? "loaded" : "loading"} onRetry={regenerate}><SectionSurface>
    {expired ? <><Text>This pairing code expired. Generate a new one.</Text><PrimaryButton label="Generate new code" onPress={regenerate} /></> : <>
      <QRCode value={pairing?.qr_payload ?? ""} size={220} />
      <Text selectable>Manual code: {pairing?.code ?? "Unknown"}</Text>
      <Text selectable>Session ID: {pairing?.session_id ?? "Unknown"}</Text>
      <Text selectable>Child profile ID: {childId}</Text><Text>Expires in: {remaining}</Text>
    </>}
  </SectionSurface></DataState></ScreenScaffold>;
}
