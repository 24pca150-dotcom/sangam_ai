import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PoemDetailComponent } from './poem-detail.component';

describe('PoemDetailComponent', () => {
  let component: PoemDetailComponent;
  let fixture: ComponentFixture<PoemDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PoemDetailComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PoemDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
