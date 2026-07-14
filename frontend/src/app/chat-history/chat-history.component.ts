import { Component, ChangeDetectorRef } from '@angular/core';
import { ChatService, ChatMessage } from '../services/chat.service';

@Component({
  selector: 'app-chat-history',
  standalone: false,
  templateUrl: './chat-history.component.html',
  styleUrls: ['./chat-history.component.css'],
})
export class ChatHistoryComponent {
  history: ChatMessage[] = [];
  expandedIndices: Set<number> = new Set<number>();

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef
  ) {
    this.history = this.chatService.getHistory();
  }

  toggleExpand(idx: number): void {
    if (this.expandedIndices.has(idx)) {
      this.expandedIndices.delete(idx);
    } else {
      this.expandedIndices.add(idx);
    }
    this.cdr.detectChanges();
  }

  isExpanded(idx: number): boolean {
    return this.expandedIndices.has(idx);
  }

  isLongText(text: string): boolean {
    return text ? text.length > 250 : false;
  }

  getDisplayText(text: string, idx: number): string {
    if (!text) return '';
    if (this.isLongText(text) && !this.isExpanded(idx)) {
      return text.slice(0, 250) + '...';
    }
    return text;
  }

  clear() {
    this.chatService.clearHistory();
    this.history = [];
    this.expandedIndices.clear();
    this.cdr.detectChanges();
  }

  deleteItem(index: number) {
    this.chatService.deleteFromHistory(index);
    this.history = this.chatService.getHistory();
    
    const newExpanded = new Set<number>();
    this.expandedIndices.forEach(idx => {
      if (idx < index) {
        newExpanded.add(idx);
      } else if (idx > index) {
        newExpanded.add(idx - 1);
      }
    });
    this.expandedIndices = newExpanded;
    
    this.cdr.detectChanges();
  }
}
