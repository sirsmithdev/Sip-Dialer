import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { contactsApi } from '@/services/api';
import type { ContactList } from '@/types';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface ContactListDetailProps {
  list: ContactList;
  onBack: () => void;
}

export function ContactListDetail({ list, onBack }: ContactListDetailProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [validFilter, setValidFilter] = useState<boolean | undefined>(undefined);

  const pageSize = 50;

  const { data, isLoading } = useQuery({
    queryKey: ['contacts', list.id, page, search, validFilter],
    queryFn: () =>
      contactsApi.listContacts(list.id, {
        page,
        page_size: pageSize,
        search: search || undefined,
        is_valid: validFilter,
      }),
  });

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleDownload = async () => {
    try {
      const blob = await contactsApi.downloadContacts(list.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${list.name.replace(/\s+/g, '_')}_contacts.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download contacts:', error);
      alert('Failed to download contacts');
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            className="text-sm text-muted-foreground hover:text-foreground mb-2 flex items-center gap-1"
            onClick={onBack}
          >
            ← Back to lists
          </button>
          <h2 className="text-2xl font-bold">{list.name}</h2>
          {list.description && (
            <p className="text-muted-foreground">{list.description}</p>
          )}
        </div>
        <Button variant="outline" onClick={handleDownload}>
          Download CSV
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border p-4">
          <p className="text-2xl font-bold">{list.total_contacts.toLocaleString()}</p>
          <p className="text-sm text-muted-foreground">Total Contacts</p>
        </div>
        <div className="rounded-lg border p-4 bg-green-50">
          <p className="text-2xl font-bold text-green-600">
            {list.valid_contacts.toLocaleString()}
          </p>
          <p className="text-sm text-muted-foreground">Valid</p>
        </div>
        <div className="rounded-lg border p-4 bg-red-50">
          <p className="text-2xl font-bold text-red-600">
            {list.invalid_contacts.toLocaleString()}
          </p>
          <p className="text-sm text-muted-foreground">Invalid</p>
        </div>
        <div className="rounded-lg border p-4">
          <p className="text-2xl font-bold">
            {list.valid_contacts > 0
              ? ((list.valid_contacts / list.total_contacts) * 100).toFixed(1)
              : 0}
            %
          </p>
          <p className="text-sm text-muted-foreground">Valid Rate</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Input
            placeholder="Search by phone, name, or email..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button variant="outline" onClick={handleSearch}>
            Search
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={validFilter === undefined ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setValidFilter(undefined);
              setPage(1);
            }}
          >
            All
          </Button>
          <Button
            variant={validFilter === true ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setValidFilter(true);
              setPage(1);
            }}
          >
            Valid
          </Button>
          <Button
            variant={validFilter === false ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setValidFilter(false);
              setPage(1);
            }}
          >
            Invalid
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Phone Number</TableHead>
              <TableHead>E.164</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Timezone</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8">
                  Loading...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No contacts found
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((contact) => (
                <TableRow key={contact.id}>
                  <TableCell className="font-mono">{contact.phone_number}</TableCell>
                  <TableCell className="font-mono text-muted-foreground">
                    {contact.phone_number_e164 || '-'}
                  </TableCell>
                  <TableCell>
                    {contact.first_name || contact.last_name
                      ? `${contact.first_name || ''} ${contact.last_name || ''}`.trim()
                      : '-'}
                  </TableCell>
                  <TableCell>{contact.email || '-'}</TableCell>
                  <TableCell>{contact.timezone || '-'}</TableCell>
                  <TableCell>
                    {contact.is_valid ? (
                      <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-green-100 text-green-700">
                        Valid
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-red-100 text-red-700"
                        title={contact.validation_error || undefined}
                      >
                        Invalid
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data?.total || 0)} of{' '}
            {data?.total || 0} contacts
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
