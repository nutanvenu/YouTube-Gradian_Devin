import { useEffect, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import QRCode from "react-native-qrcode-svg";
import { Text } from "react-native";
import { api, Pairing } from "@/api/client";
import { DataState, ScreenScaffold, SectionSurface } from "@/design-system";

export default function ParentPairingRoute() {
  const { familyId, childId } = useLocalSearchParams<{ familyId: string; childId: string }>();
  const [pairing, setPairing] = useState<Pairing | null>(null);
  const [remaining, setRemaining] = useState<string>("Unknown");
  useEffect(() => { api.createPairing(familyId, childId).then(setPairing).catch(() => setPairing(null)); }, [childId, familyId]);
  useEffect(() => {
    if (!pairing) return;
    const update = () => {
      const seconds = Math.max(0, Math.floor((new Date(pairing.expires_at).getTime() - Date.now()) / 1000));
      setRemaining(`${Math.floor(seconds / 60)}m ${seconds % 60}s`);
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, [pairing]);
  return <ScreenScaffold title="Pair a child device"><DataState state={pairing ? "loaded" : "loading"}><SectionSurface><QRCode value={pairing?.qr_payload ?? ""} size={220} /><Text selectable>Manual code: {pairing?.code ?? "Unknown"}</Text><Text>Expires in: {remaining}</Text></SectionSurface></DataState></ScreenScaffold>;
}
