import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { PoemSearchComponent } from './components/poem-search/poem-search.component';
import { PoemDetailComponent } from './components/poem-detail/poem-detail.component';
import { ChatInterfaceComponent } from './components/chat-interface/chat-interface.component';
import { AdminUploadComponent } from './components/admin-upload/admin-upload.component';
import { ExploreComponent } from './components/explore/explore.component';
import { CoursePlayerComponent } from './components/course-player/course-player.component';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'search', component: PoemSearchComponent },
  { path: 'explore', component: ExploreComponent },
  { path: 'course/:id', component: CoursePlayerComponent },
  { path: 'poem/:id', component: PoemDetailComponent },
  { path: 'chat', component: ChatInterfaceComponent },
  { path: 'admin', component: AdminUploadComponent },
  { path: '**', redirectTo: '' }
];
