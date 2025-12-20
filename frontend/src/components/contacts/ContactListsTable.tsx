import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contactsApi } from '@/services/api';
import { usePermissions } from '@/hooks/use-permissions';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface ContactListsTableProps {
  onSelectList: (list: ContactList) => void;
  onUploadClick?: () => void;
}

export function ContactListsTable({ onSelectList, onUploadClick }: ContactListsTableProps) {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [listToDelete, setListToDelete] = useState<ContactList | null>(null);

  const pageSize = 10;
  const canDelete = hasPermission('contacts.delete');
  const canImport = hasPermission('contacts.import');

  const { data, isLoading, error } = useQuery({
    queryKey: ['contactLists', page, search],
    queryFn: () => contactsApi.listContactLists({ page, page_size: pageSize, search: search || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => contactsApi.deleteContactList(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contactLists'] });
      setDeleteDialogOpen(false);
      setListToDelete(null);
    },
  });

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleDeleteClick = (list: ContactList) => {
    setListToDelete(list);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (listToDelete) {
      deleteMutation.mutate(listToDelete.id);
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-800">Failed to load contact lists. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Search and Actions */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <Input
            placeholder="Search lists..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button variant="outline" onClick={handleSearch}>
            Search
          </Button>
        </div>
        {canImport && (
          <Button onClick={onUploadClick}>
            Upload Contacts
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Valid</TableHead>
              <TableHead>Invalid</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  Loading...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No contact lists found. Upload a CSV or Excel file to get started.
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((list) => (
                <TableRow key={list.id}>
                  <TableCell className="font-medium">
                    <button
                      className="hover:underline text-left"
                      onClick={() => onSelectList(list)}
                    >
                      {list.name}
                    </button>
                    {list.description && (
                      <p className="text-sm text-muted-foreground truncate max-w-xs">
                        {list.description}
                      </p>
                    )}
                  </TableCell>
                  <TableCell>{list.total_contacts.toLocaleString()}</TableCell>
                  <TableCell className="text-green-600">
                    {list.valid_contacts.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-red-600">
                    {list.invalid_contacts.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        list.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {list.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(list.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onSelectList(list)}
                      >
                        View
                      </Button>
                      {canDelete && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-600 hover:text-red-700"
                          onClick={() => handleDeleteClick(list)}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
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
            Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data?.total || 0)} of {data?.total || 0} lists
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
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
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Contact List</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{listToDelete?.name}"? This will permanently remove
              all {listToDelete?.total_contacts.toLocaleString()} contacts in this list.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
