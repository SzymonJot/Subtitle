const API_BASE = '/api';

export async function createJob(file: File, episodeName: string): Promise<{ job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('episode_name', episodeName);

    const response = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to create job: ${error}`);
    }

    return response.json();
}

export async function triggerAnalysis(jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/manual`, {
        method: 'POST',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to trigger analysis: ${error}`);
    }

    return response.json();
}

export async function fetchAnalysis(jobId: string): Promise<any> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/analysis`, {
        method: 'GET',
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to fetch analysis: ${error}`);
    }

    return response.json();
}

export async function createDeck(analysisData: any): Promise<any> {
    const response = await fetch(`${API_BASE}/deck`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(analysisData),
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to create deck: ${error}`);
    }

    return response.json();
}

export async function exportDeck(jobId: string, deckId: string, options?: { includeSentence: boolean }): Promise<Blob> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/deck`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            deck_id: deckId,
            output_format: 'quizlet',
            export_options: {
                include_sentence: options?.includeSentence ?? false
            }
        }),
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to export deck: ${error}`);
    }

    const blob = await response.blob();
    return blob;
}

export function downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}