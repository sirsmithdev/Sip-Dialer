import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Plus, Upload, Ban, Search, MoreHorizontal, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { contactsApi } from '@/services/api';
import { ContactListsTable, ContactUploadDialog, ContactListDetail } from '@/components/contacts';
import type { ContactList, DNCEntry } from '@/types';

export function ContactsPage() {
  const [activeTab, setActiveTab] = useState('lists');
  const [selectedList, setSelectedList] = useState<ContactList | null>(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDNCDialog, setShowDNCDialog] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [newListDescription, setNewListDescription] = useState('');
  const [newDNCNumber, setNewDNCNumber] = useState('');
  const [newDNCReason, setNewDNCReason] = useState('');
  const [dncSearch, setDncSearch] = useState('');
  const [dncPage, setDncPage] = useState(1);

  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // DNC List Query
  const { data: dncData, isLoading: dncLoading } = useQuery({
    queryKey: ['dnc', dncPage, dncSearch],
    queryFn: () => contactsApi.listDNCEntries({ page: dncPage, page_size: 20, search: dncSearch || undefined }),
    enabled: activeTab === 'dnc',
  });

  // Create empty contact list mutation
  const createListMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      contactsApi.createContactList(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contact-lists'] });
      setShowCreateDialog(false);
      setNewListName('');
      setNewListDescription('');
      toast({
        title: 'Contact list created',
        description: 'Your new contact list has been created.',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create contact list.',
        variant: 'destructive',
      });
    },
  });

  // Add DNC entry mutation
  const addDNCMutation = useMutation({
    mutationFn: (data: { phone_number: string; reason?: string }) =>
      contactsApi.addDNCEntry(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dnc'] });
      setShowDNCDialog(false);
      setNewDNCNumber('');
      setNewDNCReason('');
      toast({
        title: 'DNC entry added',
        description: 'Phone number has been added to the Do-Not-Call list.',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add DNC entry. Please check the phone number format.',
        variant: 'destructive',
      });
    },
  });

  // Remove DNC entry mutation
  const removeDNCMutation = useMutation({
    mutationFn: (id: string) => contactsApi.removeDNCEntry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dnc'] });
      toast({
        title: 'DNC entry removed',
        description: 'Phone number has been removed from the Do-Not-Call list.',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to remove DNC entry.',
        variant: 'destructive',
      });
    },
  });

  const handleCreateList = () => {
    if (!newListName.trim()) return;
    createListMutation.mutate({
      name: newListName.trim(),
      description: newListDescription.trim() || undefined,
    });
  };

  const handleAddDNC = () => {
    if (!newDNCNumber.trim()) return;
    addDNCMutation.mutate({
      phone_number: newDNCNumber.trim(),
      reason: newDNCReason.trim() || undefined,
    });
  };

  const handleListSelect = (list: ContactList) => {
    setSelectedList(list);
  };

  const handleBackToLists = () => {
    setSelectedList(null);
  };

  const handleUploadComplete = () => {
    setShowUploadDialog(false);
    queryClient.invalidateQueries({ queryKey: ['contact-lists'] });
  };

  // If a list is selected, show the detail view
  if (selectedList) {
    return (
      <ContactListDetail
        list={selectedList}
        onBack={handleBackToLists}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Contacts</h1>
          <p className="text-muted-foreground">
            Manage your contact lists and Do-Not-Call registry
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === 'lists' && (
            <>
              <Button variant="outline" onClick={() => setShowCreateDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New List
              </Button>
              <Button onClick={() => setShowUploadDialog(true)}>
                <Upload className="mr-2 h-4 w-4" />
                Upload Contacts
              </Button>
            </>
          )}
          {activeTab === 'dnc' && (
            <Button onClick={() => setShowDNCDialog(true)}>
              <Ban className="mr-2 h-4 w-4" />
              Add to DNC
            </Button>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="lists">Contact Lists</TabsTrigger>
          <TabsTrigger value="dnc">Do-Not-Call</TabsTrigger>
        </TabsList>

        <TabsContent value="lists" className="mt-6">
          <ContactListsTable onSelectList={handleListSelect} />
        </TabsContent>

        <TabsContent value="dnc" className="mt-6">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search phone numbers..."
                  value={dncSearch}
                  onChange={(e) => {
                    setDncSearch(e.target.value);
                    setDncPage(1);
                  }}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phone Number</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Added</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dncLoading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : dncData?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        <p className="text-muted-foreground">No DNC entries found</p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    dncData?.items.map((entry: DNCEntry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="font-mono">{entry.phone_number}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{entry.source}</Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {entry.reason || '-'}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(entry.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => removeDNCMutation.mutate(entry.id)}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Remove
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {dncData && dncData.total > 20 && (
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Showing {((dncPage - 1) * 20) + 1} to {Math.min(dncPage * 20, dncData.total)} of {dncData.total} entries
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDncPage((p) => Math.max(1, p - 1))}
                    disabled={dncPage === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDncPage((p) => p + 1)}
                    disabled={dncPage * 20 >= dncData.total}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Upload Dialog */}
      <ContactUploadDialog
        open={showUploadDialog}
        onOpenChange={setShowUploadDialog}
        onComplete={handleUploadComplete}
      />

      {/* Create Empty List Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Contact List</DialogTitle>
            <DialogDescription>
              Create an empty contact list. You can add contacts later by uploading a file.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="list-name">Name</Label>
              <Input
                id="list-name"
                placeholder="Enter list name"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="list-description">Description (optional)</Label>
              <Textarea
                id="list-description"
                placeholder="Enter list description"
                value={newListDescription}
                onChange={(e) => setNewListDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateList}
              disabled={!newListName.trim() || createListMutation.isPending}
            >
              {createListMutation.isPending ? 'Creating...' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add DNC Dialog */}
      <Dialog open={showDNCDialog} onOpenChange={setShowDNCDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to Do-Not-Call List</DialogTitle>
            <DialogDescription>
              Add a phone number to prevent it from being contacted in any campaign.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="dnc-number">Phone Number</Label>
              <Input
                id="dnc-number"
                placeholder="Enter phone number"
                value={newDNCNumber}
                onChange={(e) => setNewDNCNumber(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Enter in any format. Will be normalized to E.164.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="dnc-reason">Reason (optional)</Label>
              <Textarea
                id="dnc-reason"
                placeholder="Enter reason for adding to DNC"
                value={newDNCReason}
                onChange={(e) => setNewDNCReason(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDNCDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddDNC}
              disabled={!newDNCNumber.trim() || addDNCMutation.isPending}
            >
              {addDNCMutation.isPending ? 'Adding...' : 'Add to DNC'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
