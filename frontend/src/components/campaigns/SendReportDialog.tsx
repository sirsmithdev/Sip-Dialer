import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Mail, Plus, X, Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { campaignsApi } from '@/services/api';

interface SendReportDialogProps {
  campaignId: string;
  campaignName: string;
}

export function SendReportDialog({ campaignId, campaignName }: SendReportDialogProps) {
  const [open, setOpen] = useState(false);
  const [emails, setEmails] = useState<string[]>([]);
  const [currentEmail, setCurrentEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const { toast } = useToast();

  const sendReportMutation = useMutation({
    mutationFn: (recipientEmails: string[]) =>
      campaignsApi.sendReport(campaignId, { recipient_emails: recipientEmails }),
    onSuccess: (data) => {
      toast({
        title: 'Report Sent',
        description: data.message,
      });
      setOpen(false);
      setEmails([]);
      setCurrentEmail('');
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to send report',
        variant: 'destructive',
      });
    },
  });

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const addEmail = () => {
    const email = currentEmail.trim().toLowerCase();
    setEmailError('');

    if (!email) {
      return;
    }

    if (!validateEmail(email)) {
      setEmailError('Please enter a valid email address');
      return;
    }

    if (emails.includes(email)) {
      setEmailError('This email is already added');
      return;
    }

    setEmails([...emails, email]);
    setCurrentEmail('');
  };

  const removeEmail = (emailToRemove: string) => {
    setEmails(emails.filter((e) => e !== emailToRemove));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addEmail();
    }
  };

  const handleSend = () => {
    if (emails.length === 0) {
      setEmailError('Please add at least one recipient');
      return;
    }
    sendReportMutation.mutate(emails);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <Mail className="mr-2 h-4 w-4" />
          Send Report
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Send Campaign Report
          </DialogTitle>
          <DialogDescription>
            Send a detailed report for "{campaignName}" to the specified email addresses.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Email Input */}
          <div className="space-y-2">
            <Label htmlFor="email">Recipient Email</Label>
            <div className="flex gap-2">
              <Input
                id="email"
                type="email"
                placeholder="email@example.com"
                value={currentEmail}
                onChange={(e) => {
                  setCurrentEmail(e.target.value);
                  setEmailError('');
                }}
                onKeyPress={handleKeyPress}
                className="flex-1"
              />
              <Button type="button" variant="outline" size="icon" onClick={addEmail}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {emailError && (
              <p className="text-sm text-red-600">{emailError}</p>
            )}
          </div>

          {/* Email List */}
          {emails.length > 0 && (
            <div className="space-y-2">
              <Label>Recipients ({emails.length})</Label>
              <div className="flex flex-wrap gap-2">
                {emails.map((email) => (
                  <Badge
                    key={email}
                    variant="secondary"
                    className="flex items-center gap-1 pr-1"
                  >
                    {email}
                    <button
                      type="button"
                      onClick={() => removeEmail(email)}
                      className="ml-1 rounded-full hover:bg-muted p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Info */}
          <Alert>
            <Mail className="h-4 w-4" />
            <AlertDescription>
              The report will include campaign statistics, call outcomes, and completion rates.
              It will be sent as an HTML email.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSend}
            disabled={emails.length === 0 || sendReportMutation.isPending}
          >
            {sendReportMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send Report
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
