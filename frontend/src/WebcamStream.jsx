import React, { useRef, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";

export default function WebcamStream({ target, speaking }) {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const speakRef = useRef({ lastSpoken: 0 });

  const sendFrame = async () => {
    if (!webcamRef.current || !target) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;

    const blob = await (await fetch(imageSrc)).blob();
    const formData = new FormData();
    formData.append("frame", blob, "frame.jpg");
    formData.append("target", target);

    try {
      const res = await axios.post("http://localhost:8000/detect", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      drawBox(res.data);

      if (speaking && res.data.found) {
        const now = Date.now();
        if (now - speakRef.current.lastSpoken > 1500) {
          const msg = `${res.data.label} is on your ${res.data.direction}, approximately ${res.data.distance} centimeters away`;
          speechSynthesis.cancel();
          speechSynthesis.speak(new SpeechSynthesisUtterance(msg));
          speakRef.current.lastSpoken = now;
        }
      }
    } catch (err) {
      console.log("Backend error", err);
    }
  };

  const drawBox = (data) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!data.found) return;

    const [x1, y1, x2, y2] = data.box;

    ctx.strokeStyle = "lime";
    ctx.lineWidth = 3;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    ctx.fillStyle = "yellow";
    ctx.font = "16px Arial";
    ctx.fillText(`${data.label} (${data.distance}cm)`, x1, y1 - 5);
  };

  useEffect(() => {
    const interval = setInterval(sendFrame, 500);
    return () => clearInterval(interval);
  }, [target, speaking]);

  return (
    <div className="relative w-[640px] h-[480px]">
      <Webcam
        ref={webcamRef}
        screenshotFormat="image/jpeg"
        width={640}
        height={480}
        className="rounded-lg border-2 border-gray-400"
      />
      <canvas
        ref={canvasRef}
        width={640}
        height={480}
        className="absolute top-0 left-0"
      ></canvas>
    </div>
  );
}
