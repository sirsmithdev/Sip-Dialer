import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { contactsApi } from '@/services/api';
import type { FilePreviewResponse, ColumnMapping, ImportResultResponse } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ContactUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type UploadStep = 'upload' | 'mapping' | 'result';

const TARGET_FIELDS = [
  { key: 'phone_number', label: 'Phone Number', required: true },
  { key: 'first_name', label: 'First Name', required: false },
  { key: 'last_name', label: 'Last Name', required: false },
  { key: 'email', label: 'Email', required: false },
  { key: 'timezone', label: 'Timezone', required: false },
] as const;

export function ContactUploadDialog({ open, onOpenChange }: ContactUploadDialogProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<UploadStep>('upload');
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<FilePreviewResponse | null>(null);
  const [listName, setListName] = useState('');
  const [listDescription, setListDescription] = useState('');
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ImportResultResponse | null>(null);

  const previewMutation = useMutation({
    mutationFn: (file: File) => contactsApi.previewUpload(file),
    onSuccess: (data) => {
      setPreview(data);
      // Initialize mapping with suggestions
      const initialMapping: Record<string, string> = {};
      if (data.suggested_mapping.phone_number) {
        initialMapping.phone_number = data.suggested_mapping.phone_number;
      }
      if (data.suggested_mapping.first_name) {
        initialMapping.first_name = data.suggested_mapping.first_name;
      }
      if (data.suggested_mapping.last_name) {
        initialMapping.last_name = data.suggested_mapping.last_name;
      }
      if (data.suggested_mapping.email) {
        initialMapping.email = data.suggested_mapping.email;
      }
      if (data.suggested_mapping.timezone) {
        initialMapping.timezone = data.suggested_mapping.timezone;
      }
      setMapping(initialMapping);
      setListName(data.filename.replace(/\.(csv|xlsx|xls)$/i, ''));
      setStep('mapping');
    },
  });

  const importMutation = useMutation({
    mutationFn: (data: { file_id: string; name: string; description?: string; column_mapping: ColumnMapping }) =>
      contactsApi.confirmUpload(data),
    onSuccess: (data) => {
      setResult(data);
      setStep('result');
      queryClient.invalidateQueries({ queryKey: ['contactLists'] });
    },
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleFileSelect(file);
    }
  }, []);

  const handleFileSelect = (file: File) => {
    const validTypes = [
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ];
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!validTypes.includes(file.type) && !hasValidExtension) {
      alert('Please upload a CSV or Excel file');
      return;
    }

    setSelectedFile(file);
    previewMutation.mutate(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleMappingChange = (field: string, value: string) => {
    setMapping(prev => ({
      ...prev,
      [field]: value === '__none__' ? '' : value,
    }));
  };

  const handleImport = () => {
    if (!preview || !mapping.phone_number) return;

    const columnMapping: ColumnMapping = {
      phone_number: mapping.phone_number,
      first_name: mapping.first_name || undefined,
      last_name: mapping.last_name || undefined,
      email: mapping.email || undefined,
      timezone: mapping.timezone || undefined,
    };

    importMutation.mutate({
      file_id: preview.file_id,
      name: listName,
      description: listDescription || undefined,
      column_mapping: columnMapping,
    });
  };

  const handleClose = () => {
    setStep('upload');
    setSelectedFile(null);
    setPreview(null);
    setListName('');
    setListDescription('');
    setMapping({});
    setResult(null);
    onOpenChange(false);
  };

  const isImportValid = mapping.phone_number && listName.trim();

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {step === 'upload' && 'Upload Contacts'}
            {step === 'mapping' && 'Map Columns'}
            {step === 'result' && 'Import Complete'}
          </DialogTitle>
          <DialogDescription>
            {step === 'upload' && 'Upload a CSV or Excel file with your contacts'}
            {step === 'mapping' && 'Map your file columns to contact fields'}
            {step === 'result' && 'Your contacts have been imported'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Upload */}
        {step === 'upload' && (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? 'border-primary bg-primary/5' : 'border-gray-300'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {previewMutation.isPending ? (
              <div className="py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Processing file...</p>
              </div>
            ) : (
              <>
                <div className="mb-4">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    stroke="currentColor"
                    fill="none"
                    viewBox="0 0 48 48"
                  >
                    <path
                      d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <p className="text-lg mb-2">
                  Drag and drop your file here, or{' '}
                  <label className="text-primary cursor-pointer hover:underline">
                    browse
                    <input
                      type="file"
                      className="hidden"
                      accept=".csv,.xlsx,.xls"
                      onChange={handleFileInputChange}
                    />
                  </label>
                </p>
                <p className="text-sm text-muted-foreground">
                  Supports CSV and Excel files (max 10MB)
                </p>
              </>
            )}
            {previewMutation.isError && (
              <p className="text-red-600 mt-4">
                Failed to process file. Please check the format and try again.
              </p>
            )}
          </div>
        )}

        {/* Step 2: Column Mapping */}
        {step === 'mapping' && preview && (
          <div className="space-y-6">
            {/* List Name */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="listName">List Name *</Label>
                <Input
                  id="listName"
                  value={listName}
                  onChange={(e) => setListName(e.target.value)}
                  placeholder="My Contact List"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="listDescription">Description</Label>
                <Input
                  id="listDescription"
                  value={listDescription}
                  onChange={(e) => setListDescription(e.target.value)}
                  placeholder="Optional description"
                />
              </div>
            </div>

            {/* Column Mapping */}
            <div className="space-y-4">
              <h3 className="font-medium">Column Mapping</h3>
              <p className="text-sm text-muted-foreground">
                Match your file columns to contact fields. Phone Number is required.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {TARGET_FIELDS.map((field) => (
                  <div key={field.key} className="space-y-2">
                    <Label>
                      {field.label}
                      {field.required && <span className="text-red-500 ml-1">*</span>}
                    </Label>
                    <Select
                      value={mapping[field.key] || '__none__'}
                      onValueChange={(value) => handleMappingChange(field.key, value)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select column" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">-- Don't import --</SelectItem>
                        {preview.columns.map((col) => (
                          <SelectItem key={col} value={col}>
                            {col}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>
            </div>

            {/* Preview Table */}
            <div className="space-y-2">
              <h3 className="font-medium">Preview ({preview.row_count.toLocaleString()} rows total)</h3>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {preview.columns.map((col) => (
                        <TableHead key={col} className="whitespace-nowrap">
                          {col}
                          {mapping.phone_number === col && (
                            <span className="ml-1 text-xs text-green-600">(Phone)</span>
                          )}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.preview_rows.slice(0, 5).map((row, idx) => (
                      <TableRow key={idx}>
                        {preview.columns.map((col) => (
                          <TableCell key={col} className="whitespace-nowrap max-w-xs truncate">
                            {String(row[col] ?? '')}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Results */}
        {step === 'result' && result && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-lg border p-4 text-center">
                <p className="text-2xl font-bold">{result.total_rows.toLocaleString()}</p>
                <p className="text-sm text-muted-foreground">Total Rows</p>
              </div>
              <div className="rounded-lg border p-4 text-center bg-green-50">
                <p className="text-2xl font-bold text-green-600">
                  {result.valid_contacts.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Imported</p>
              </div>
              <div className="rounded-lg border p-4 text-center bg-red-50">
                <p className="text-2xl font-bold text-red-600">
                  {result.invalid_contacts.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Invalid</p>
              </div>
              <div className="rounded-lg border p-4 text-center bg-yellow-50">
                <p className="text-2xl font-bold text-yellow-600">
                  {(result.duplicate_contacts + result.dnc_contacts).toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Skipped</p>
              </div>
            </div>

            {result.errors.length > 0 && (
              <div className="space-y-2">
                <h3 className="font-medium text-red-600">
                  Errors (showing first {Math.min(result.errors.length, 10)})
                </h3>
                <div className="rounded-md border overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Row</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>Error</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.errors.slice(0, 10).map((error, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{error.row}</TableCell>
                          <TableCell>{error.phone_number || '-'}</TableCell>
                          <TableCell className="text-red-600">{error.error}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === 'mapping' && (
            <>
              <Button variant="outline" onClick={() => setStep('upload')}>
                Back
              </Button>
              <Button
                onClick={handleImport}
                disabled={!isImportValid || importMutation.isPending}
              >
                {importMutation.isPending ? 'Importing...' : 'Import Contacts'}
              </Button>
            </>
          )}
          {step === 'result' && (
            <Button onClick={handleClose}>Done</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
