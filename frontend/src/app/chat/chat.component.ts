import { Component, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';
import { ChatService } from '../services/chat.service';

@Component({
  selector: 'app-chat',
  standalone: false,
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css'],
})
export class ChatComponent {
  chatForm = this.fb.group({
    question: ['', Validators.required],
  });

  answer = '';
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private chatService: ChatService,
    private cdr: ChangeDetectorRef
  ) {}

  ask(): void {
    if (!this.chatForm.valid) {
      return;
    }

    this.isLoading = true;
    this.answer = '';
    this.cdr.detectChanges();
    const question = this.chatForm.value.question!;
    this.chatService.queryStream(question).subscribe({
      next: (chunk) => {
        this.answer += chunk;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Streaming error:', err);
        if (!this.answer) {
          this.answer = 'Unable to fetch an answer. Please try again.';
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.chatService.saveToHistory(question, this.answer);
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  copyAnswer(): void {
    if (this.answer) {
      navigator.clipboard.writeText(this.answer);
    }
  }
}
