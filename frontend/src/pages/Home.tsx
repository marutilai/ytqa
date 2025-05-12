import { useState } from 'react'
import CopyButton from '../components/CopyButton';

interface VideoInfo {
  video_id: string;
  num_segments: number;
  segments: TranscriptSegment[];
}

interface TranscriptSegment {
  text: string;
  start: number;
  duration: number;
}

interface TopicBlock {
  title: string;
  start: number;
  segments: TranscriptSegment[];
}

interface ChatMessage {
  question: string;
  answer: string;
  timestamp: number;
}

export default function Home() {
  const [videoUrl, setVideoUrl] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null)
  const [topics, setTopics] = useState<TopicBlock[]>([])
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
  const [currentQuestion, setCurrentQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)

  const validateYouTubeUrl = (url: string) => {
    try {
      const parsed = new URL(url);
      if (
        (parsed.hostname === "www.youtube.com" || parsed.hostname === "youtube.com") &&
        parsed.pathname === "/watch"
      ) {
        const v = parsed.searchParams.get("v");
        return v && v.length === 11;
      }
      if (
        (parsed.hostname === "youtu.be" || parsed.hostname === "www.youtu.be") &&
        parsed.pathname.length === 12 // "/<11-char-id>"
      ) {
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const handleProcessVideo = async () => {
    // Clear previous state
    setError(null);
    setVideoInfo(null);
    setTopics([]);
    setChatHistory([]);

    // Validate URL
    if (!validateYouTubeUrl(videoUrl)) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    try {
      setIsProcessing(true);
      const response = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: videoUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to process video');
      }

      const data: VideoInfo = await response.json();
      setVideoInfo(data);

      // Fetch topics
      const topicsResponse = await fetch(`/api/topics/${data.video_id}`);
      if (!topicsResponse.ok) {
        throw new Error('Failed to fetch video topics');
      }
      const topicsData: TopicBlock[] = await topicsResponse.json();
      setTopics(topicsData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process video');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleJumpToTime = (seconds: number) => {
    if (!videoInfo?.video_id) return;
    window.open(`https://youtube.com/watch?v=${videoInfo.video_id}&t=${Math.floor(seconds)}`, '_blank');
  };

  const handleAskQuestion = async () => {
    if (!currentQuestion.trim() || !videoInfo) return;

    setIsAsking(true);
    setError(null);

    try {
      // Convert chat history to the format expected by the API
      const formattedHistory = chatHistory.flatMap(msg => [
        { role: 'user', content: msg.question },
        { role: 'assistant', content: msg.answer }
      ]);

      const response = await fetch('http://localhost:8000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentQuestion,
          video_id: videoInfo.video_id,
          conversation_history: formattedHistory
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get answer');
      }

      const data = await response.json();
      
      setChatHistory([
        ...chatHistory,
        {
          question: currentQuestion,
          answer: data.answer,
          timestamp: Date.now(),
        },
      ]);
      
      setCurrentQuestion('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer');
      console.error(err);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header with Search */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-gray-900">YouTube QA</h1>
            <div className="flex-1 flex gap-2">
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleProcessVideo()}
                placeholder="Enter YouTube URL..."
                className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                disabled={isProcessing}
              />
              <button
                onClick={handleProcessVideo}
                disabled={isProcessing || !videoUrl.trim()}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isProcessing ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Processing...
                  </>
                ) : (
                  'Process'
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        {/* Three-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Transcript Pane */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Transcript</h2>
              {videoInfo?.segments && videoInfo.segments.length > 0 && (
                <CopyButton 
                  text={videoInfo.segments.map(segment => 
                    `[${new Date(segment.start * 1000).toISOString().substr(11, 8)}] ${segment.text}`
                  ).join('\n')} 
                />
              )}
            </div>
            <div className="p-4 h-[600px] overflow-y-auto">
              {videoInfo?.segments ? (
                <div className="space-y-4">
                  {videoInfo.segments.map((segment, index) => (
                    <div 
                      key={index} 
                      className="flex gap-4 hover:bg-gray-50 p-2 rounded cursor-pointer"
                      onClick={() => handleJumpToTime(segment.start)}
                    >
                      <span className="text-sm text-gray-500 whitespace-nowrap hover:text-blue-600">
                        {new Date(segment.start * 1000).toISOString().substr(11, 8)}
                      </span>
                      <p className="text-gray-700">{segment.text}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  No transcript available
                </div>
              )}
            </div>
          </div>

          {/* Topics Pane */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-semibold">Topics</h2>
              {topics.length > 0 && (
                <CopyButton 
                  text={topics.map(topic => 
                    `[${new Date(topic.start * 1000).toISOString().substr(11, 8)}]\n${topic.title}\n${topic.segments[0]?.text || ''}`
                  ).join('\n\n')} 
                />
              )}
            </div>
            <div className="p-4 h-[600px] overflow-y-auto">
              {topics.length > 0 ? (
                <div className="space-y-6">
                  {topics.map((topic, index) => (
                    <div key={index} className="border-b pb-4 last:border-b-0">
                      <div 
                        className="flex items-start gap-3 cursor-pointer hover:bg-gray-50 p-2 rounded"
                        onClick={() => handleJumpToTime(topic.start)}
                      >
                        <span className="text-sm text-blue-600 whitespace-nowrap">
                          {new Date(topic.start * 1000).toISOString().substr(11, 8)}
                        </span>
                        <div>
                          <h3 className="font-medium text-gray-900">{topic.title}</h3>
                          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                            {topic.segments[0]?.text}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  {isProcessing ? 'Analyzing topics...' : 'No topics available'}
                </div>
              )}
            </div>
          </div>

          {/* Chat Pane */}
          <div className="bg-white rounded-lg shadow flex flex-col">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold">Ask Questions</h2>
            </div>
            <div className="flex-1 p-4 overflow-y-auto">
              {chatHistory.length > 0 ? (
                <div className="space-y-4">
                  {chatHistory.map((message, index) => (
                    <div key={index} className="flex flex-col">
                      <div className="group bg-blue-50 rounded-lg p-3 max-w-[80%] relative">
                        <p className="text-gray-700 pr-16">{message.question}</p>
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <CopyButton text={message.question} />
                        </div>
                      </div>
                      <div className="group mt-2 bg-gray-50 rounded-lg p-3 max-w-[80%] ml-auto relative">
                        <p className="text-gray-700 whitespace-pre-wrap pr-16">{message.answer}</p>
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <CopyButton text={message.answer} />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  Ask questions about the video
                </div>
              )}
            </div>
            <div className="p-4 border-t">
              <div className="flex gap-2">
                <textarea
                  value={currentQuestion}
                  onChange={(e) => setCurrentQuestion(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleAskQuestion()}
                  placeholder="Ask a question about the video..."
                  className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 resize-none"
                  rows={1}
                  disabled={!videoInfo || isAsking}
                />
                <button
                  onClick={handleAskQuestion}
                  disabled={!currentQuestion.trim() || !videoInfo || isAsking}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isAsking ? (
                    <>
                      <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Thinking...
                    </>
                  ) : (
                    'Send'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 