import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { LoginComponent } from './login/login.component';
import { ChatComponent } from './chat/chat.component';
import { UploadComponent } from './upload/upload.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { DocumentsComponent } from './documents/documents.component';
import { ChatHistoryComponent } from './chat-history/chat-history.component';
import { AuthInterceptor } from './auth.interceptor';
import { RegisterComponent } from './register/register.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    ChatComponent,
    UploadComponent,
    SidebarComponent,
    DocumentsComponent,
    ChatHistoryComponent,
    RegisterComponent,
  ],
  imports: [BrowserModule, HttpClientModule, ReactiveFormsModule],
  providers: [
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
