import { useState } from "react"

export default function ObjectFinder() {
  const [status, setStatus] = useState("idle")
  const [command, setCommand] = useState("")
  const [isListening, setIsListening] = useState(false)

  const speak = (text) => {
    const msg = new SpeechSynthesisUtterance(text)
    msg.lang = "en-US"
    window.speechSynthesis.speak(msg)
  }

  const voiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      speak("Voice recognition not supported.")
      return
    }

    setIsListening(true)
    const recog = new SpeechRecognition()
    recog.lang = "en-US"
    recog.start()
    speak("Listening...")

    recog.onresult = async (event) => {
      const text = event.results[0][0].transcript
      setCommand(text)
      setStatus("processing")

      try {
        await fetch("http://localhost:8000/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ target: text }),
        })
        setStatus("running")
      } catch (error) {
        console.error("Error:", error)
        setStatus("idle")
      }
      setIsListening(false)
    }

    recog.onerror = () => {
      setIsListening(false)
      setStatus("idle")
    }
  }

  const getStatusDisplay = () => {
    switch (status) {
      case "idle":
        return "Ready to detect objects"
      case "processing":
        return `Processing: "${command}"`
      case "running":
        return `🎯 Detecting: "${command}" - Check camera window`
      default:
        return "Ready to detect objects"
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case "idle":
        return "text-slate-300"
      case "processing":
        return "text-amber-300"
      case "running":
        return "text-emerald-300"
      default:
        return "text-slate-300"
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center text-white p-4">
      <div className="w-full max-w-2xl">
        {/* Header Section */}
        <div className="text-center mb-12 space-y-3">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 bg-cyan-500 rounded-lg flex items-center justify-center">
              <span className="text-xl">👁️</span>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Object Finder
            </h1>
          </div>
          <p className="text-slate-400 text-lg">Voice-controlled object detection for accessibility</p>
        </div>

        {/* Status Card */}
        <div className="bg-slate-700/50 backdrop-blur border border-slate-600 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
            <p className="text-xs uppercase tracking-widest text-slate-400">Status</p>
          </div>
          <p className={`text-2xl font-semibold ${getStatusColor()} transition-colors duration-300`}>
            {getStatusDisplay()}
          </p>
        </div>

        {/* Main Controls */}
        <div className="space-y-4 mb-8">
          {/* Start Button */}
          <button
            onClick={voiceInput}
            disabled={isListening}
            className={`w-full py-8 cursor-pointer px-6 rounded-xl text-xl font-bold transition-all duration-200 flex items-center justify-center gap-3 ${
              isListening
                ? "bg-blue-500/40 cursor-not-allowed border-2 border-blue-400 animate-pulse"
                : "bg-blue-600 hover:bg-blue-700 active:scale-95 border-2 border-blue-500 hover:border-blue-400 shadow-lg hover:shadow-blue-500/50"
            }`}
            aria-label="Start voice detection"
          >
            <span className="text-3xl">🎤</span>
            <span>{isListening ? "Listening..." : "Start Detection"}</span>
          </button>

          {/* Help Button */}
          <button
            onClick={() =>
              speak(
                "Press the Start Detection button and say the object you want to find. For example, say 'find my phone' or 'find my book'.",
              )
            }
            className="w-full cursor-pointer py-4 px-6 rounded-xl text-base font-semibold transition-all duration-200 bg-slate-700 hover:bg-slate-600 border border-slate-500 hover:border-slate-400 active:scale-95 flex items-center justify-center gap-3"
            aria-label="Get help instructions"
          >
            <span className="text-2xl">❓</span>
            <span>How to use</span>
          </button>
        </div>

        {/* Info Section */}
        <div className="bg-slate-700/30 border border-slate-600 rounded-xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-slate-200">Quick Tips</h2>
          <ul className="space-y-3 text-slate-300 text-sm">
            <li className="flex gap-3">
              <span className="text-cyan-400 font-bold flex-shrink-0">1.</span>
              <span>Click "Start Detection" or say the object name clearly</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyan-400 font-bold flex-shrink-0">2.</span>
              <span>The app will begin searching using your camera</span>
            </li>
            <li className="flex gap-3">
              <span className="text-cyan-400 font-bold flex-shrink-0">3.</span>
              <span>Audio feedback will guide you to the detected object</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
