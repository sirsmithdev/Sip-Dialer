import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { audioApi } from '@/services/api';
import type { AudioFile, AudioStatus } from '@/types';

const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.gsm', '.ulaw', '.alaw'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getStatusBadgeClass(status: AudioStatus): string {
  switch (status) {
    case 'ready':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-yellow-100 text-yellow-800';
    case 'uploading':
      return 'bg-blue-100 text-blue-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function AudioSettingsTab() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadName, setUploadName] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [audioToDelete, setAudioToDelete] = useState<AudioFile | null>(null);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  // Fetch audio files
  const { data: audioData, isLoading, error } = useQuery({
    queryKey: ['audioFiles'],
    queryFn: () => audioApi.list({ page: 1, page_size: 100 }),
    refetchInterval: 5000, // Refetch every 5 seconds to check processing status
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({
      file,
      name,
      description,
    }: {
      file: File;
      name: string;
      description?: string;
    }) => audioApi.upload(file, name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audioFiles'] });
      setIsUploadDialogOpen(false);
      setSelectedFile(null);
      setUploadName('');
      setUploadDescription('');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { is_active?: boolean };
    }) => audioApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audioFiles'] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => audioApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audioFiles'] });
      setIsDeleteDialogOpen(false);
      setAudioToDelete(null);
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setFileError(null);

    if (file) {
      // Validate extension
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setFileError(`Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
        return;
      }

      // Validate size
      if (file.size > MAX_FILE_SIZE) {
        setFileError(`File too large. Maximum size: ${formatFileSize(MAX_FILE_SIZE)}`);
        return;
      }

      setSelectedFile(file);
      // Auto-fill name from filename without extension
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
      setUploadName(nameWithoutExt);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFile && uploadName.trim()) {
      uploadMutation.mutate({
        file: selectedFile,
        name: uploadName.trim(),
        description: uploadDescription.trim() || undefined,
      });
    }
  };

  const handleToggleActive = (audio: AudioFile) => {
    updateMutation.mutate({
      id: audio.id,
      data: { is_active: !audio.is_active },
    });
  };

  const handleDeleteClick = (audio: AudioFile) => {
    setAudioToDelete(audio);
    setIsDeleteDialogOpen(true);
  };

  const handlePlayAudio = (audio: AudioFile) => {
    if (playingAudioId === audio.id) {
      setPlayingAudioId(null);
    } else {
      setPlayingAudioId(audio.id);
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-lg border p-6">
        <p className="text-muted-foreground">Loading audio files...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border p-6">
        <p className="text-red-600">Failed to load audio files. Please try again.</p>
      </div>
    );
  }

  const audioFiles = audioData?.items || [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Audio Files</CardTitle>
            <CardDescription>
              Manage audio files for use in campaigns. Files are automatically transcoded to
              telephony-compatible formats.
            </CardDescription>
          </div>
          <Button onClick={() => setIsUploadDialogOpen(true)}>Upload Audio</Button>
        </CardHeader>
        <CardContent>
          {audioFiles.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">No audio files uploaded yet.</p>
              <Button variant="outline" onClick={() => setIsUploadDialogOpen(true)}>
                Upload Your First Audio File
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Format</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audioFiles.map((audio) => (
                  <TableRow key={audio.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{audio.name}</p>
                        {audio.description && (
                          <p className="text-sm text-muted-foreground">{audio.description}</p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="uppercase">{audio.original_format}</TableCell>
                    <TableCell>{formatDuration(audio.duration_seconds)}</TableCell>
                    <TableCell>{formatFileSize(audio.file_size_bytes)}</TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(
                          audio.status
                        )}`}
                      >
                        {audio.status}
                      </span>
                      {audio.error_message && (
                        <p className="text-xs text-red-600 mt-1">{audio.error_message}</p>
                      )}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={audio.is_active}
                        onCheckedChange={() => handleToggleActive(audio)}
                        disabled={audio.status !== 'ready'}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {audio.status === 'ready' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handlePlayAudio(audio)}
                          >
                            {playingAudioId === audio.id ? 'Stop' : 'Play'}
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => handleDeleteClick(audio)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Audio Player */}
          {playingAudioId && (
            <div className="mt-4 p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium mb-2">Now Playing:</p>
              <audio
                controls
                autoPlay
                src={`/api/v1/audio/${playingAudioId}/stream?format=wav`}
                onEnded={() => setPlayingAudioId(null)}
                className="w-full"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Audio File</DialogTitle>
            <DialogDescription>
              Upload an audio file (MP3, WAV, GSM, ULAW, ALAW). Maximum size: 50MB. Files will be
              automatically transcoded to telephony-compatible formats.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUploadSubmit}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="audio-file">Audio File</Label>
                <Input
                  id="audio-file"
                  type="file"
                  accept=".mp3,.wav,.gsm,.ulaw,.alaw"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                />
                {fileError && <p className="text-sm text-red-600">{fileError}</p>}
                {selectedFile && (
                  <p className="text-sm text-muted-foreground">
                    Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="audio-name">Display Name</Label>
                <Input
                  id="audio-name"
                  placeholder="Enter a name for this audio file"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="audio-description">Description (Optional)</Label>
                <Input
                  id="audio-description"
                  placeholder="Enter an optional description"
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsUploadDialogOpen(false);
                  setSelectedFile(null);
                  setUploadName('');
                  setUploadDescription('');
                  setFileError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedFile || !uploadName.trim() || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </DialogFooter>
            {uploadMutation.error && (
              <p className="text-sm text-red-600 mt-2">
                Failed to upload file. Please try again.
              </p>
            )}
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Audio File</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{audioToDelete?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false);
                setAudioToDelete(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => audioToDelete && deleteMutation.mutate(audioToDelete.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
          {deleteMutation.error && (
            <p className="text-sm text-red-600 mt-2">
              Failed to delete file. Please try again.
            </p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
