import React, { useState } from 'react';
import { Sparkles, Play, Search, Layers, Download, AlertCircle } from 'lucide-react';
import StepCard from '@/components/ui/StepCard';
import ActionButton from '@/components/ui/ActionButton';
import FileUpload from '@/components/FileUpload';
import AnalysisPreview from '@/components/AnalysisPreview';
import { Input } from '@/components/ui/input';
import { createJob, triggerAnalysis, fetchAnalysis, createDeck, exportDeck, downloadBlob } from '@/components/api';

export default function Home() {
  // State
  const [file, setFile] = useState(null);
  const [episodeName, setEpisodeName] = useState('');
  const [jobId, setJobId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [deckCreated, setDeckCreated] = useState(false);
  const [error, setError] = useState(null);

  // Loading states
  const [creatingJob, setCreatingJob] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [fetchingAnalysis, setFetchingAnalysis] = useState(false);
  const [creatingDeck, setCreatingDeck] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Derived states
  const canCreateJob = file && episodeName.trim();
  const canRunAnalysis = jobId && !analysis;
  const canCreateDeck = analysis && !deckCreated;
  const canExport = deckCreated;

  const getStepStatus = (step) => {
    switch (step) {
      case 1:
        if (jobId) return 'completed';
        if (creatingJob) return 'loading';
        if (file || episodeName) return 'active';
        return 'pending';
      case 2:
        if (analysis) return 'completed';
        if (runningAnalysis || fetchingAnalysis) return 'loading';
        if (jobId) return 'active';
        return 'pending';
      case 3:
        if (deckCreated) return 'completed';
        if (creatingDeck) return 'loading';
        if (analysis) return 'active';
        return 'pending';
      case 4:
        if (exporting) return 'loading';
        if (deckCreated) return 'active';
        return 'pending';
      default:
        return 'pending';
    }
  };

  const handleCreateJob = async () => {
    setError(null);
    setCreatingJob(true);
    try {
      const result = await createJob(file, episodeName);
      setJobId(result.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingJob(false);
    }
  };

  const handleRunAnalysis = async () => {
    setError(null);
    setRunningAnalysis(true);
    try {
      await triggerAnalysis(jobId);
      setRunningAnalysis(false);
      setFetchingAnalysis(true);
      const result = await fetchAnalysis(jobId);
      setAnalysis(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningAnalysis(false);
      setFetchingAnalysis(false);
    }
  };

  const handleCreateDeck = async () => {
    setError(null);
    setCreatingDeck(true);
    try {
      await createDeck(analysis);
      setDeckCreated(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingDeck(false);
    }
  };

  const handleExport = async () => {
    setError(null);
    setExporting(true);
    try {
      const blob = await exportDeck(jobId);
      downloadBlob(blob, `${episodeName || 'flashcards'}.tsv`);
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setEpisodeName('');
    setJobId(null);
    setAnalysis(null);
    setDeckCreated(false);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800/50">
        <div className="max-w-3xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-violet-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight">Persdeck</h1>
                <p className="text-xs text-zinc-500">Subtitle → Flashcards</p>
              </div>
            </div>
            {jobId && (
              <ActionButton
                variant="ghost"
                size="sm"
                onClick={handleReset}
              >
                Start over
              </ActionButton>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-6 py-10">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400">Something went wrong</p>
              <p className="text-sm text-red-400/70 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* Step 1: Upload */}
          <StepCard
            stepNumber={1}
            title="Upload Subtitle File"
            description="Select an .srt file and name your episode"
            status={getStepStatus(1)}
            disabled={false}
          >
            <div className="space-y-4">
              <FileUpload
                file={file}
                onFileSelect={setFile}
                disabled={!!jobId}
              />

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">
                  Episode Name
                </label>
                <Input
                  type="text"
                  placeholder="e.g., Breaking Bad S01E01"
                  value={episodeName}
                  onChange={(e) => setEpisodeName(e.target.value)}
                  disabled={!!jobId}
                  className="bg-zinc-800/50 border-zinc-700 focus:border-violet-500 focus:ring-violet-500/20 placeholder:text-zinc-600"
                />
              </div>

              {!jobId && (
                <ActionButton
                  onClick={handleCreateJob}
                  disabled={!canCreateJob}
                  loading={creatingJob}
                  icon={Play}
                  className="w-full"
                >
                  Create Job
                </ActionButton>
              )}

              {jobId && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-zinc-800/30 border border-zinc-700/50">
                  <span className="text-xs text-zinc-500">Job ID:</span>
                  <code className="text-sm font-mono text-violet-400">{jobId}</code>
                </div>
              )}
            </div>
          </StepCard>

          {/* Step 2: Analyze */}
          <StepCard
            stepNumber={2}
            title="Run Analysis"
            description="Extract vocabulary and phrases from your subtitles"
            status={getStepStatus(2)}
            disabled={!jobId}
          >
            <div className="space-y-4">
              {!analysis && (
                <ActionButton
                  onClick={handleRunAnalysis}
                  disabled={!canRunAnalysis}
                  loading={runningAnalysis || fetchingAnalysis}
                  icon={Search}
                  className="w-full"
                >
                  {runningAnalysis ? 'Analyzing...' : fetchingAnalysis ? 'Fetching results...' : 'Start Analysis'}
                </ActionButton>
              )}

              {analysis && (
                <AnalysisPreview data={analysis} />
              )}
            </div>
          </StepCard>

          {/* Step 3: Create Deck */}
          <StepCard
            stepNumber={3}
            title="Create Deck"
            description="Generate flashcards from the analysis"
            status={getStepStatus(3)}
            disabled={!analysis}
          >
            <div className="space-y-4">
              {!deckCreated ? (
                <ActionButton
                  onClick={handleCreateDeck}
                  disabled={!canCreateDeck}
                  loading={creatingDeck}
                  icon={Layers}
                  className="w-full"
                >
                  Create Flashcard Deck
                </ActionButton>
              ) : (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <Layers className="w-4 h-4 text-emerald-500" />
                  <span className="text-sm text-emerald-400">Deck created successfully</span>
                </div>
              )}
            </div>
          </StepCard>

          {/* Step 4: Export */}
          <StepCard
            stepNumber={4}
            title="Export to Quizlet"
            description="Download your flashcards as a TSV file"
            status={getStepStatus(4)}
            disabled={!deckCreated}
          >
            <ActionButton
              onClick={handleExport}
              disabled={!canExport}
              loading={exporting}
              icon={Download}
              variant="secondary"
              className="w-full"
            >
              Download TSV File
            </ActionButton>
          </StepCard>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/50 mt-20">
        <div className="max-w-3xl mx-auto px-6 py-6">
          <p className="text-xs text-zinc-600 text-center">
            Persdeck MVP • Upload subtitles, create flashcards
          </p>
        </div>
      </footer>
    </div>
  );
}