import { Stream, ProviderContext } from "../types";

export const getStream = async function ({
  link: url,
  type,
  providerContext,
}: {
  link: string;
  type: string;
  providerContext: ProviderContext;
}): Promise<Stream[]> {
  try {
    const data = JSON.parse(url);
    if (!data || !data.url) {
      console.log("getStream error: No URL found in data");
      return [];
    }

    const videoUrl = data.url;
    const serverName = data.title || "Unknown Server";
    const userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

    // --- SMART CHECK: লিংকটি জীবিত কিনা তা যাচাই করা ---
    let isAlive = true;
    try {
      const controller = new AbortController();
      // ৪ সেকেন্ডের মধ্যে রেসপন্স না আসলে চেক বাতিল করবে (টাইমআউট)
      const timeoutId = setTimeout(() => controller.abort(), 4000);

      // Range: bytes=0-0 মানে সার্ভারকে শুধু প্রথম ১ বাইট ডেটা দিতে বলা
      const check = await fetch(videoUrl, {
        method: "GET",
        headers: { 
          "Range": "bytes=0-0", 
          "User-Agent": userAgent 
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // 200 (OK), 206 (Partial Content), 403 (Forbidden) মানে লিংক কাজ করছে
      if (!check.ok && check.status !== 206 && check.status !== 403) {
        console.warn(`[movieBox] Dead stream link skipped: ${videoUrl}`);
        isAlive = false;
      }
    } catch (e) {
      // কিছু পুরোনো ডিভাইস (যেমন TV) বা সার্ভার Range রিকোয়েস্ট সাপোর্ট না করলে 
      // বা নেটওয়ার্ক এরর হলে, আমরা ধরে নেব লিংকটি ভালো আছে (যাতে ভুলভাবে বাদ না পড়ে)।
      console.warn(`[movieBox] Link check failed, assuming alive for: ${videoUrl}`);
      isAlive = true; 
    }

    if (!isAlive) {
      return []; // মৃত লিংক প্লেয়ারে পাঠানো হলো না
    }

    // --- লিংক ঠিক থাকলে স্ট্রিম তৈরি ---
    const stream: Stream[] = [{
      link: videoUrl,
      server: serverName,
      type: "mp4",
    }];

    console.log("stream generated successfully", stream);
    return stream;

  } catch (err) {
    console.log("getStream error", err);
    return [];
  }
};
