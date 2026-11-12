// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

import ChatInput from './ChatInput.jsx';
import { ScheduleButton } from './schedule/ScheduleDialog.jsx';
import SubstitutionMatcher from './transcript/SubstitutionMatcher.jsx';
import TranscriptUploadProvider, {
  TranscriptUploadButton,
} from './transcript/TranscriptUpload.jsx';

// jsdom does not implement <dialog> open/close, so stub them.
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function showModal() {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function close() {
    this.open = false;
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('ChatInput interactions', () => {
  it('sends trimmed text on Enter and clears the box', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const box = screen.getByPlaceholderText('Ask a question…');

    await userEvent.type(box, '  what is next?  {Enter}');

    expect(onSubmit).toHaveBeenCalledWith('what is next?');
    expect(box.value).toBe('');
  });

  it('keeps Shift+Enter as a new line', async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);

    await userEvent.type(screen.getByPlaceholderText('Ask a question…'), 'line one{Shift>}{Enter}{/Shift}line two');

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('sends from the Send button and stays disabled while busy', async () => {
    const onSubmit = vi.fn();
    const { rerender } = render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const button = screen.getByRole('button', { name: 'Send' });

    expect(button.disabled).toBe(true);
    await userEvent.type(screen.getByPlaceholderText('Ask a question…'), 'hello');
    await userEvent.click(button);
    expect(onSubmit).toHaveBeenCalledWith('hello');

    rerender(<ChatInput onSubmit={onSubmit} disabled />);
    await userEvent.type(screen.getByPlaceholderText('Ask a question…'), 'again');
    expect(screen.getByRole('button', { name: 'Send' }).disabled).toBe(true);
  });
});

describe('ScheduleButton interactions', () => {
  it('opens the schedule dialog when clicked', async () => {
    render(<ScheduleButton scheduleService={{ buildSchedule: vi.fn() }} />);

    await userEvent.click(screen.getByRole('button', { name: 'Schedule' }));

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
  });
});

describe('SubstitutionMatcher interactions', () => {
  const requirements = [{ code: 'MSSE 635', title: 'Architecture', credits: 3 }];
  const courses = [{ code: 'MSES 602', title: 'DevOps', credits: 3 }];

  it('saves an empty set of assignments by default', async () => {
    const onSave = vi.fn();
    render(
      <SubstitutionMatcher requirements={requirements} courses={courses} onSave={onSave} />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Save substitutions' }));

    expect(onSave).toHaveBeenCalledWith({});
  });

  it('saves the assignments it started with', async () => {
    const onSave = vi.fn();
    render(
      <SubstitutionMatcher
        requirements={requirements}
        courses={courses}
        initialAssignments={{ 'MSSE 635': 'MSES 602' }}
        onSave={onSave}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Save substitutions' }));

    expect(onSave).toHaveBeenCalledWith({ 'MSSE 635': 'MSES 602' });
  });
});

describe('TranscriptUpload interactions', () => {
  function renderUpload(transcriptService) {
    return render(
      <TranscriptUploadProvider transcriptService={transcriptService}>
        <TranscriptUploadButton />
      </TranscriptUploadProvider>,
    );
  }

  it('uploads the chosen PDF and reports the result', async () => {
    const transcriptService = {
      uploadTranscript: vi.fn().mockResolvedValue({
        saved: [{ code: 'MSSE 601' }],
        skipped: [],
        clearedSubstitutions: [],
      }),
    };
    const { container } = renderUpload(transcriptService);
    await userEvent.click(screen.getByRole('button', { name: 'Upload transcript' }));

    const pdf = new File(['%PDF-1.4'], 'transcript.pdf', { type: 'application/pdf' });
    await userEvent.upload(container.querySelector('input[type="file"]'), pdf);
    await userEvent.click(screen.getByRole('button', { name: 'Upload and replace' }));

    await waitFor(() => {
      expect(screen.getByText('Transcript updated')).toBeTruthy();
    });
    expect(transcriptService.uploadTranscript).toHaveBeenCalledWith(pdf);
  });

  it('shows an error when the upload fails', async () => {
    const transcriptService = {
      uploadTranscript: vi.fn().mockRejectedValue(new Error('Parse failed')),
    };
    const { container } = renderUpload(transcriptService);
    await userEvent.click(screen.getByRole('button', { name: 'Upload transcript' }));
    const pdf = new File(['%PDF-1.4'], 'bad.pdf', { type: 'application/pdf' });
    await userEvent.upload(container.querySelector('input[type="file"]'), pdf);

    await userEvent.click(screen.getByRole('button', { name: 'Upload and replace' }));

    await waitFor(() => {
      expect(screen.getByText('Parse failed')).toBeTruthy();
    });
    expect(transcriptService.uploadTranscript).toHaveBeenCalledTimes(1);
  });
});
