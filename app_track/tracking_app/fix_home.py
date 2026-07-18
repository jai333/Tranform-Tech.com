with open('templates/tracking_app/home.html', 'r') as f:
    content = f.read()

# We need to insert `            </div>\n        </div>\n` right before `        <!-- IT Ticketing Showcase -->`
if "                    </div>\n                </div>\n        <!-- IT Ticketing Showcase -->" in content:
    # already fixed? No
    pass

# Let's just do a string replacement
bad_block = """                    <div class="sf-badge sf-badge-bottom">
                        <i class='bx bx-trending-up' style="color:#10b981;"></i>
                        <span>+40% Close Rate</span>
                    </div>
                </div>
        <!-- IT Ticketing Showcase -->"""

good_block = """                    <div class="sf-badge sf-badge-bottom">
                        <i class='bx bx-trending-up' style="color:#10b981;"></i>
                        <span>+40% Close Rate</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- IT Ticketing Showcase -->"""

if bad_block in content:
    content = content.replace(bad_block, good_block)
    
    # We also need to remove the two extra </div> at the end of Cybersecurity showcase before </div></div></section>
    # The end looks like:
    #                 </div>
    #             </div>
    #         </div>
    # 
    #             </div>
    #         </div>
    #     </div>
    # </section>
    
    tail_bad = """                </div>
            </div>
        </div>

            </div>
        </div>
    </div>
</section>"""

    tail_good = """                </div>
            </div>
        </div>
    </div>
</section>"""
    
    content = content.replace(tail_bad, tail_good)
    
    with open('templates/tracking_app/home.html', 'w') as f:
        f.write(content)
    print("Fixed layout")
else:
    print("Bad block not found")
