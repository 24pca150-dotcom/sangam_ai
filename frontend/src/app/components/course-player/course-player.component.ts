import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { ChatInterfaceComponent } from '../chat-interface/chat-interface.component';

@Component({
  selector: 'app-course-player',
  standalone: true,
  imports: [CommonModule, RouterModule, ChatInterfaceComponent],
  templateUrl: './course-player.component.html',
  styleUrls: ['./course-player.component.css']
})
export class CoursePlayerComponent implements OnInit {
  poem: any = null;
  loading = true;
  poemId: string | null = null;
  videoUrl: string = '';

  constructor(private route: ActivatedRoute, private api: ApiService) {}

  ngOnInit() {
    this.poemId = this.route.snapshot.paramMap.get('id');
    
    if (this.poemId === '87') {
      this.videoUrl = 'https://res.cloudinary.com/demo/video/upload/v1692275685/elephants.mp4';
    } else if (this.poemId === '101') {
      this.videoUrl = 'https://res.cloudinary.com/demo/video/upload/v1692275685/sea_turtle.mp4';
    } else {
      this.videoUrl = 'https://res.cloudinary.com/demo/video/upload/v1692275685/elephants.mp4';
    }

    if (this.poemId) {
      this.api.getPoem(this.poemId).subscribe({
        next: (res) => {
          this.poem = res;
          this.loading = false;
        },
        error: (err) => {
          console.error('Error fetching poem', err);
          this.loading = false;
        }
      });
    } else {
      this.loading = false;
    }
  }
}
