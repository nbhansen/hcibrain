"use client";

import { useState } from "react";
import { type Highlight, HighlightOverlay } from "./highlight-overlay";

interface MockPDFProps {
  highlights: Highlight[];
  highlightsEnabled: boolean;
  highlightOpacity: number;
}

export function MockPDF({ highlights, highlightsEnabled, highlightOpacity }: MockPDFProps) {
  const [scale, _setScale] = useState(1);

  // Sample paper content with paragraphs that would have highlights
  return (
    <div className="relative bg-white p-8 shadow-md w-full max-w-4xl mx-auto">
      <div className="relative">
        {/* Paper title */}
        <h1 className="text-2xl font-bold mb-4 text-center">
          Deep Speech 2: End-to-End Speech Recognition
        </h1>

        {/* Authors */}
        <p className="text-center mb-8 text-gray-600">Authors: John Doe, Jane Smith, et al.</p>

        {/* Abstract */}
        <h2 className="text-xl font-semibold mb-2">Abstract</h2>
        <p className="mb-4">
          We present a state-of-the-art speech recognition system developed using end-to-end deep
          learning. Our system, Deep Speech 2, outperforms previously published results on several
          speech recognition benchmarks and can be trained using either English or Mandarin speech.
        </p>

        {/* Introduction */}
        <h2 className="text-xl font-semibold mb-2">1. Introduction</h2>
        <p className="mb-4">
          Speech recognition systems traditionally comprised many hand-engineered components. In
          contrast, our system is trained end-to-end using deep learning, requiring minimal human
          effort for its creation and optimization.
        </p>

        {/* Goal section */}
        <p className="mb-4">
          Our goal is to build a speech recognition system that can handle most applications with
          robustness to variation in environment, speaker accent and noise, without additional
          training for the transcription task. We believe that a single engine must learn to be
          similarly competent, able to handle most applications with only minor modifications and
          able to learn new languages from scratch without dramatic changes.
        </p>

        {/* Method section */}
        <h2 className="text-xl font-semibold mb-2">2. Method</h2>
        <p className="mb-4">
          Since Deep Speech 2 (DS2) is an end-to-end deep learning system, we can achieve
          performance gains by focusing on three crucial components: the model architecture, large
          labeled training datasets, and computational scale. This approach has also yielded great
          advances in other application areas such as computer vision and natural language
          processing.
        </p>

        <p className="mb-4">
          As a result, in several cases, our system is competitive with the transcription of human
          workers when benchmarked on standard datasets. Page 1
        </p>

        {/* Results section */}
        <h2 className="text-xl font-semibold mb-2">3. Results</h2>
        <p className="mb-4">
          Since our system is built on end-to-end deep learning, we can employ a spectrum of deep
          learning techniques: capturing large training sets, training larger models with high
          performance computing, and methodically exploring the space of neural network
          architectures.
        </p>

        <p className="mb-4">
          We show that through these techniques we are able to reduce error rates of our previous
          end-to-end system in English by up to 43%, and can also recognize Mandarin speech with
          high accuracy.
        </p>

        {/* Conclusion */}
        <h2 className="text-xl font-semibold mb-2">4. Conclusion</h2>
        <p className="mb-4">
          We have the innate ability to learn any language during childhood, using general skills to
          learn language. After learning to read and write, most humans can transcribe speech with
          robustness to variation in environment, speaker accent and noise, without additional
          training for the transcription task.
        </p>

        {/* Highlight overlay */}
        <HighlightOverlay
          highlights={highlights}
          currentPage={1}
          opacity={highlightOpacity}
          enabled={highlightsEnabled}
          scale={scale}
        />
      </div>
    </div>
  );
}
