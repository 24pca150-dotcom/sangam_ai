import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { PURANANURU_POETS } from '../../data/purananuru-data';

@Component({
  selector: 'app-explore',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './explore.component.html',
  styleUrls: ['./explore.component.css']
})
export class ExploreComponent {
  activeTab: 'poems' | 'analysis' = 'poems';
  poets = PURANANURU_POETS;
  Math = Math;
  
  searchQuery = '';
  currentPage = 1;
  itemsPerPage = 10;

  get filteredPoets() {
    let result = this.poets;
    if (this.searchQuery && this.searchQuery.trim() !== '') {
      // Handle common Tamil typing mistake: ா (aa modifier) + ் (dot) instead of ர் (ra + dot)
      // They look visually identical but have different Unicode.
      const q = this.searchQuery.trim().toLowerCase().replace(/ா்/g, 'ர்');
      
      result = result.filter(p => {
        // Match Poet Name (normalize poet name too just in case)
        const normalizedPoet = p.poet.toLowerCase().replace(/ா்/g, 'ர்');
        if (normalizedPoet.includes(q)) return true;
        
        // Match Serial Number
        if (p.sno.toString() === q) return true;
        
        // Match exact poem number in the songs string
        const songNumbers = p.songs.split(',').map(s => s.trim());
        if (songNumbers.includes(q)) return true;
        
        // Fallback to general substring match
        if (p.songs.includes(q)) return true;
        
        return false;
      });
    }
    return result;
  }

  get paginatedPoets() {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    return this.filteredPoets.slice(startIndex, startIndex + this.itemsPerPage);
  }

  get totalPages() {
    return Math.ceil(this.filteredPoets.length / this.itemsPerPage) || 1;
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  onSearchChange() {
    this.currentPage = 1;
  }
}
