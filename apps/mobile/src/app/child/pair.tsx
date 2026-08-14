import { useState } from "react";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useRouter } from "expo-router";
import { Text } from "react-native";
import * as ed25519 from "@noble/ed25519";
import { api, ApiError, sessionStorage } from "@/api/client";
import { PrimaryButton, ScreenScaffold, SectionSurface, TextField } from "@/design-system";

function toBase64(bytes: Uint8Array): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  let output = "";
  for (let index = 0; index < bytes.length; index += 3) {
    const first = bytes[index];
    const second = bytes[index + 1] ?? 0;
    const third = bytes[index + 2] ?? 0;
    output += alphabet[first >> 2];
    output += alphabet[((first & 3) << 4) | (second >> 4)];
    output += index + 1 < bytes.length ? alphabet[((second & 15) << 2) | (third >> 6)] : "=";
    output += index + 2 < bytes.length ? alphabet[third & 63] : "=";
  }
  return output;
}

export default function ChildPairRoute() {
  const router = useRouter();
  const [permission, requestPermission] = useCameraPermissions();
  const [code, setCode] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [childId, setChildId] = useState("");
  const [message, setMessage] = useState("Scan the parent QR code or enter its six digits.");
  const [scanning, setScanning] = useState(false);
  const redeem = async () => {
    try {
      const privateKey = ed25519.utils.randomSecretKey();
      const publicKey = await ed25519.getPublicKeyAsync(privateKey);
      const credentials = await api.redeemPairing({ session_id: sessionId, code, child_profile_id: childId, platform: "ANDROID", public_key: toBase64(publicKey) });
      await sessionStorage.setDevicePrivateKey(toBase64(privateKey));
      await sessionStorage.setDeviceToken(credentials.device_token);
      router.replace("/child/home");
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "Pairing failed. Check the code and try again."); }
  };
  return <ScreenScaffold title="Set up child device"><SectionSurface><PrimaryButton label="Scan QR code" onPress={() => { if (!permission?.granted) void requestPermission(); setScanning(true); }} />{scanning && permission?.granted ? <CameraView style={{ height: 220 }} onBarcodeScanned={({ data }) => { setScanning(false); const parsed = data.match(/pair\/([^?]+)\?code=(\d{6})/); if (parsed) { setSessionId(parsed[1]); setCode(parsed[2]); } }} /> : null}<TextField label="Session ID" value={sessionId} onChangeText={setSessionId} /><TextField label="Six-digit code" value={code} onChangeText={setCode} keyboardType="numeric" /><TextField label="Child profile ID" value={childId} onChangeText={setChildId} /><Text accessibilityLiveRegion="polite">{message}</Text><PrimaryButton label="Pair device" onPress={redeem} disabled={!sessionId || code.length !== 6 || !childId} /></SectionSurface></ScreenScaffold>;
}
