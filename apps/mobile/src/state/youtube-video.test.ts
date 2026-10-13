/// <reference types="node" />
import { runInNewContext } from "node:vm";
import { isAllowedYouTubeNavigation, videoIdFromUrl, PLAY_GATE_SCRIPT } from "./youtube-video";

function playbackGate(url = "https://m.youtube.com/watch?v=abcdefghijk") {
  let now = 1_000;
  const video = { paused: false, pause: jest.fn() };
  const callbacks: Array<() => void> = [];
  const listeners: Record<string, (event: { target: typeof video }) => void> = {};
  const window = {
    __guardianHold: false, __guardianAllowed: {} as Record<string, number>,
    __guardianSettings: { youtube_paused: false },
    ReactNativeWebView: { postMessage: jest.fn() },
  };
  runInNewContext(PLAY_GATE_SCRIPT, {
    window, location: new URL(url), Date: { now: () => now },
    document: {
      addEventListener: (type: string, listener: (event: { target: typeof video }) => void) => { listeners[type] = listener; },
      querySelectorAll: () => [video],
    },
    setInterval: (callback: () => void) => callbacks.push(callback),
  });
  return { window, video, play: () => listeners.play({ target: video }), tick: () => callbacks.forEach((callback) => callback()), advance: (milliseconds: number) => { now += milliseconds; } };
}

describe("WebView playback permission", () => {
  it("holds playback before approval and permits only the exact unexpired video", () => {
    const gate = playbackGate();
    gate.play();
    expect(gate.video.pause).toHaveBeenCalledTimes(1);
    gate.video.pause.mockClear();
    gate.window.__guardianHold = false;
    gate.window.__guardianAllowed.abcdefghijk = 15_000;
    gate.play();
    expect(gate.video.pause).not.toHaveBeenCalled();
    gate.advance(15_000);
    gate.tick();
    expect(gate.video.pause).toHaveBeenCalled();
    expect(gate.window.__guardianHold).toBe(true);
    expect(gate.window.ReactNativeWebView.postMessage).toHaveBeenCalledWith(JSON.stringify({ type: "lease-expired" }));
  });

  it("a parent pause and SOS hold override a live playback grant", () => {
    const gate = playbackGate();
    gate.window.__guardianAllowed.abcdefghijk = 15_000;
    gate.window.__guardianHold = false;
    gate.window.__guardianSettings.youtube_paused = true;
    gate.play();
    expect(gate.video.pause).toHaveBeenCalledTimes(1);
    gate.window.__guardianSettings.youtube_paused = false;
    gate.window.__guardianHold = true;
    gate.play();
    expect(gate.video.pause).toHaveBeenCalledTimes(2);
  });

  it("does not permit another video or unidentified homepage previews", () => {
    for (const url of ["https://m.youtube.com/watch?v=otherVideo1", "https://m.youtube.com/"]) {
      const gate = playbackGate(url);
      gate.window.__guardianHold = false;
      gate.window.__guardianAllowed.abcdefghijk = 15_000;
      gate.play();
      expect(gate.video.pause).toHaveBeenCalled();
    }
  });
});

describe("videoIdFromUrl", () => {
  it("reads watch, shorts and short-link URLs", () => {
    expect(videoIdFromUrl("https://m.youtube.com/watch?v=dQw4w9WgXcQ&pp=abc")).toBe("dQw4w9WgXcQ");
    expect(videoIdFromUrl("https://www.youtube.com/shorts/abcdefghijk")).toBe("abcdefghijk");
    expect(videoIdFromUrl("https://youtu.be/abcdefghijk")).toBe("abcdefghijk");
    expect(videoIdFromUrl("https://music.youtube.com/watch?v=abcdefghijk")).toBe("abcdefghijk");
  });

  it("ignores non-video YouTube pages and other hosts", () => {
    expect(videoIdFromUrl("https://m.youtube.com/results?search_query=cats")).toBeNull();
    expect(videoIdFromUrl("https://example.com/watch?v=abcdefghijk")).toBeNull();
    expect(videoIdFromUrl("not a url")).toBeNull();
  });
});

describe("isAllowedYouTubeNavigation", () => {
  it("keeps navigation inside YouTube and Google sign-in", () => {
    expect(isAllowedYouTubeNavigation("https://m.youtube.com/results?search_query=cats")).toBe(true);
    expect(isAllowedYouTubeNavigation("https://youtu.be/abcdefghijk")).toBe(true);
    expect(isAllowedYouTubeNavigation("https://accounts.google.com/ServiceLogin")).toBe(true);
    expect(isAllowedYouTubeNavigation("about:blank")).toBe(true);
  });

  it("blocks app links, advertisers and look-alike hosts", () => {
    expect(isAllowedYouTubeNavigation("intent://watch?v=abcdefghijk#Intent;package=com.google.android.youtube;end")).toBe(false);
    expect(isAllowedYouTubeNavigation("vnd.youtube:abcdefghijk")).toBe(false);
    expect(isAllowedYouTubeNavigation("https://www.audiusa.com/")).toBe(false);
    expect(isAllowedYouTubeNavigation("https://www.google.com/search?q=x")).toBe(false);
    expect(isAllowedYouTubeNavigation("https://notyoutube.com/")).toBe(false);
    expect(isAllowedYouTubeNavigation("http://m.youtube.com/watch?v=abcdefghijk")).toBe(false);
    expect(isAllowedYouTubeNavigation("data:text/html,<video>")).toBe(false);
    expect(isAllowedYouTubeNavigation("blob:https://m.youtube.com/abc")).toBe(false);
  });
});
